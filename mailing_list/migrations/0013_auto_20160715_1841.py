# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0012_supersender'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseSettings',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('canvas_course_id', models.IntegerField()),
                ('alwaysMailStaff', models.NullBooleanField(default=True)),
                ('modified_by', models.CharField(max_length=32, null=True)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, null=True)),
                ('date_modified', models.DateTimeField(default=django.utils.timezone.now, null=True)),
            ],
            options={
                'db_table': 'ml_course_settings',
            },
        ),
        migrations.AddField(
            model_name='mailinglist',
            name='course_settings',
            field=models.ForeignKey(to='mailing_list.CourseSettings', null=True),
        ),
    ]
