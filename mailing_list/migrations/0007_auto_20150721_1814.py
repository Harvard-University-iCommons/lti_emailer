# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0006_mailinglist_access_level'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mailinglist',
            name='access_level',
            field=models.CharField(default=b'members', max_length=32, blank=True),
        ),
    ]
