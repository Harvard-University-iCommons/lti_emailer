# -*- coding: utf-8 -*-


from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0012_supersender'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseSettings',
            fields=[
                ('canvas_course_id', models.IntegerField(serialize=False,
                                                         primary_key=True)),
                ('always_mail_staff', models.BooleanField(default=True)),
                ('modified_by', models.CharField(max_length=32, null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'ml_course_settings',
            },
        ),
        migrations.AlterField(
            model_name='mailinglist',
            name='date_created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='mailinglist',
            name='date_modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='mailinglist',
            name='course_settings',
            field=models.ForeignKey(to='mailing_list.CourseSettings', null=True, on_delete=django.db.models.deletion.CASCADE),
        ),
    ]
