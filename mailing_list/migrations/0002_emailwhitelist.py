# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailWhitelist',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=254)),
            ],
            options={
                'db_table': 'ml_email_whitelist',
            },
        ),
    ]
