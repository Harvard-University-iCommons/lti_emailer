# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0005_auto_20150413_2122'),
    ]

    operations = [
        migrations.AddField(
            model_name='mailinglist',
            name='access_level',
            field=models.CharField(max_length=32, null=True, blank=True),
        ),
    ]
