
import itertools

from django.db import migrations

# Adds new roles to the lti_permissions table with the same permissions that are mapped over from their equivalent
# previous role. There are 4 roles that are by default, not allowed in all schools.

NEW_ROLES_MAP = {
    'Faculty': ['Instructor', 'Primary Instructor', 'Secondary Instructor'],
    'TeacherEnrollment': ['TF/TA', 'Faculty Assistant'],
    'Teaching Staff': ['Preceptor'],
    'Student': ['Enrollee'],
    'Prospective Enrollee': ['Petitioner', 'Waitlisted'],
}

PERMISSION_NAMES = ['lti_emailer_send_all',
                    'lti_emailer_view']

NEW_ROLES = [
    'Instructor',
    'Primary Instructor',
    'Secondary Instructor',
    'TF/TA',
    'Faculty Assistant',
    'Preceptor',
]

NOT_ALLOWED_ROLES = [
    'Enrollee',
    'Petitioner',
    'Waitlisted',
    'Course Assistant'
]


def create_permissions(apps, schema_editor):
    permission_class = apps.get_model('lti_permissions',
                                      'LtiPermission')

    # Make sure to rename all Course Head roles to Head Instructor prior to creating the new permissions
    permission_class.objects.filter(canvas_role='Course Head').update(canvas_role='Head Instructor')

    all_permissions = permission_class.objects.all()

    # Create the new set of permissions mapped from the current permissions role
    for old_permission in all_permissions:
        try:
            new_roles = NEW_ROLES_MAP[old_permission.canvas_role]
            for new_role in new_roles:
                permission_class(permission=old_permission.permission,
                                 canvas_role=new_role,
                                 school_id=old_permission.school_id,
                                 allow=old_permission.allow).save()
        except KeyError:
            # Roles that are not being mapped are not included in the mapping dict and will cause a KeyError
            pass

    # Explicitly set Enrollee, Petitioner, Course Assistant and Waitlisted roles to False for all schools
    for role in NOT_ALLOWED_ROLES:
        for permission in PERMISSION_NAMES:
            permission_class(permission=permission,
                             canvas_role=role,
                             school_id='*',
                             allow=False).save()


def reverse_permissions_load(apps, schema_editor):
    permission_class = apps.get_model('lti_permissions',
                                      'LtiPermission')
    permission_class.objects.filter(
        canvas_role__in=NEW_ROLES,
        permission__in=PERMISSION_NAMES,
    ).delete()

    permission_class.objects.filter(
        canvas_role__in=NOT_ALLOWED_ROLES,
        permission__in=PERMISSION_NAMES,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('mailing_list', '0013_create_course_settings_model_and_update_mailing_list_date_fields'),
    ]

    operations = [
        migrations.RunPython(
            code=create_permissions,
            reverse_code=reverse_permissions_load,
        ),
    ]
