import csv
import logging
import sys
from datetime import timezone as dt_timezone

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from mailing_list.models import MailingList

logger = logging.getLogger(__name__)

ACCESS_LEVEL_TO_V2 = {
    MailingList.ACCESS_LEVEL_MEMBERS: {"valid_senders": "all_members", "active": True},
    MailingList.ACCESS_LEVEL_EVERYONE: {"valid_senders": "all_members", "active": True},
    MailingList.ACCESS_LEVEL_STAFF: {"valid_senders": "staff_only", "active": True},
    MailingList.ACCESS_LEVEL_READONLY: {
        "valid_senders": "all_members",
        "active": False,
    },
}

ACTION_WRITTEN = "written"
ACTION_SKIPPED_EXISTING = "skipped_existing"
ACTION_ERROR = "errors"
ACTION_DRY_RUN = "dry_run"


class Command(BaseCommand):
    help = "Copies all existing MailingList records into a DynamoDB table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-file",
            help="Write a CSV of per-list results to this path.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do everything except the DynamoDB put_item calls.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace existing items instead of skipping them.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        overwrite = options["overwrite"]

        table = None if dry_run else self._get_table()

        counts = {
            ACTION_WRITTEN: 0,
            ACTION_SKIPPED_EXISTING: 0,
            ACTION_ERROR: 0,
            ACTION_DRY_RUN: 0,
        }
        results = []

        rows = MailingList.objects.all().select_related("course_settings").iterator()
        for ml in rows:
            try:
                item = self._to_dynamo_item(ml)
            except ValueError as e:
                logger.warning(
                    "Skipping MailingList id=%s due to mapping error: %s",
                    ml.id,
                    e,
                    extra={
                        "canvas_course_id": ml.canvas_course_id,
                        "section_id": ml.section_id,
                    },
                )
                counts[ACTION_ERROR] += 1
                results.append(
                    {
                        "canvas_course_id": ml.canvas_course_id,
                        "section_id": ml.section_id,
                        "list_key": None,
                        "action": ACTION_ERROR,
                        "error": str(e),
                    }
                )
                continue

            action, err = self._put(table, item, overwrite=overwrite, dry_run=dry_run)
            counts[action] += 1
            results.append(
                {
                    "canvas_course_id": ml.canvas_course_id,
                    "section_id": ml.section_id,
                    "list_key": item["SK"].removeprefix("SETTINGS#"),
                    "action": action,
                    "error": err,
                }
            )

        self._report(counts, results, options)

        if counts[ACTION_ERROR]:
            sys.exit(1)

    def _get_table(self):
        table_name = settings.DYNAMODB_TABLE_NAME
        if not table_name:
            raise CommandError(
                "DYNAMODB_TABLE_NAME is not configured. Set dynamodb_table_name "
                "in SECURE_SETTINGS."
            )
        return boto3.resource("dynamodb", region_name=settings.AWS_REGION).Table(
            table_name
        )

    def _to_dynamo_item(self, ml):
        mapping = ACCESS_LEVEL_TO_V2.get(ml.access_level)
        if mapping is None:
            raise ValueError(f"Unknown access_level: {ml.access_level!r}")

        if ml.section_id is None:
            list_key = f"canvas-{ml.canvas_course_id}"
        else:
            list_key = f"canvas-{ml.canvas_course_id}-{ml.section_id}"

        include_all_staff = (
            ml.course_settings.always_mail_staff
            if ml.course_settings is not None
            else True
        )

        item = {
            "PK": f"COURSE#{ml.canvas_course_id}",
            "SK": f"SETTINGS#{list_key}",
            "course_id": ml.canvas_course_id,
            "active": mapping["active"],
            "deleted": False,
            "valid_senders": mapping["valid_senders"],
            "include_all_staff": include_all_staff,
            "created_by": ml.created_by,
            "created_at": _to_iso_utc(ml.date_created),
            "updated_at": _to_iso_utc(ml.date_modified),
        }

        if ml.section_id is not None:
            item["section_id"] = ml.section_id
        if ml.modified_by:
            item["updated_by"] = ml.modified_by

        return item

    def _put(self, table, item, overwrite, dry_run):
        if dry_run:
            logger.debug("[dry-run] Would put item %s", item)
            return ACTION_DRY_RUN, None

        kwargs = {"Item": item}
        if not overwrite:
            kwargs["ConditionExpression"] = "attribute_not_exists(PK)"

        try:
            table.put_item(**kwargs)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code == "ConditionalCheckFailedException":
                return ACTION_SKIPPED_EXISTING, None
            logger.error(
                "DynamoDB put_item failed for %s: %s",
                item["SK"],
                e,
                extra={"item": item},
            )
            return ACTION_ERROR, str(e)

        return ACTION_WRITTEN, None

    def _report(self, counts, results, options):
        summary = (
            f"Wrote {counts[ACTION_WRITTEN]} / "
            f"skipped {counts[ACTION_SKIPPED_EXISTING]} / "
            f"errors {counts[ACTION_ERROR]} / "
            f"dry-run {counts[ACTION_DRY_RUN]} "
            f"(total rows: {len(results)})"
        )
        self.stdout.write(summary)

        output_file = options.get("output_file")
        if output_file:
            with open(output_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["canvas_course_id", "section_id", "list_key", "action", "error"]
                )
                for r in results:
                    writer.writerow(
                        [
                            r["canvas_course_id"],
                            r["section_id"] if r["section_id"] is not None else "",
                            r["list_key"] or "",
                            r["action"],
                            r["error"] or "",
                        ]
                    )


def _to_iso_utc(dt):
    return dt.astimezone(dt_timezone.utc).isoformat()
