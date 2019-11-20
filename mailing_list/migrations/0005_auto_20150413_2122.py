# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0004_remove_mailinglist_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mailinglist',
            name='section_id',
            field=models.IntegerField(),
        ),
    ]
