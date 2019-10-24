# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0009_auto_20150727_1530'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='unsubscribed',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='unsubscribed',
            name='mailing_list',
        ),
        migrations.RemoveField(
            model_name='mailinglist',
            name='subscriptions_updated',
        ),
        migrations.DeleteModel(
            name='Unsubscribed',
        ),
    ]
