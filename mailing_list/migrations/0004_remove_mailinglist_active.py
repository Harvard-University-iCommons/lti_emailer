# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0003_data_add_whitelist_members'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='mailinglist',
            name='active',
        ),
    ]
