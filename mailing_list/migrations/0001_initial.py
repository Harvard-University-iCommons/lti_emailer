# -*- coding: utf-8 -*-


from django.db import models, migrations
import datetime
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MailingList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('canvas_course_id', models.IntegerField()),
                ('section_id', models.IntegerField(null=True, blank=True)),
                ('active', models.BooleanField(default=False)),
                ('created_by', models.CharField(max_length=32)),
                ('modified_by', models.CharField(max_length=32)),
                ('date_created', models.DateTimeField(default=datetime.datetime.utcnow, blank=True)),
                ('date_modified', models.DateTimeField(default=datetime.datetime.utcnow, blank=True)),
                ('subscriptions_updated', models.DateTimeField(null=True, blank=True)),
            ],
            options={
                'db_table': 'ml_mailing_list',
            },
        ),
        migrations.CreateModel(
            name='Unsubscribed',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=254)),
                ('created_by', models.CharField(max_length=32)),
                ('date_created', models.DateTimeField(default=datetime.datetime.utcnow, blank=True)),
                ('mailing_list', models.ForeignKey(to='mailing_list.MailingList', on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
                'db_table': 'ml_unsubscribed',
            },
        ),
        migrations.AlterUniqueTogether(
            name='mailinglist',
            unique_together=set([('canvas_course_id', 'section_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='unsubscribed',
            unique_together=set([('mailing_list', 'email')]),
        ),
    ]
