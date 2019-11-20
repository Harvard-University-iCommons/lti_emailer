# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0011_auto_20150908_1505'),
    ]

    operations = [
        migrations.CreateModel(
            name='SuperSender',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=254)),
                ('school_id', models.CharField(max_length=16)),
            ],
            options={
                'db_table': 'ml_super_sender',
            },
        ),
    ]
