# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0010_auto_20150827_1712'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mailinglist',
            name='section_id',
            field=models.IntegerField(null=True),
        ),
    ]
