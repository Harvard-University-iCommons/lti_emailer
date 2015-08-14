# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0007_auto_20150721_1814'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mailinglist',
            name='access_level',
            field=models.CharField(default=b'members', max_length=32),
        ),
    ]
