# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0008_auto_20150724_1909'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mailinglist',
            name='date_created',
            field=models.DateTimeField(default=django.utils.timezone.now, blank=True),
        ),
        migrations.AlterField(
            model_name='mailinglist',
            name='date_modified',
            field=models.DateTimeField(default=django.utils.timezone.now, blank=True),
        ),
        migrations.AlterField(
            model_name='unsubscribed',
            name='date_created',
            field=models.DateTimeField(default=django.utils.timezone.now, blank=True),
        ),
    ]
