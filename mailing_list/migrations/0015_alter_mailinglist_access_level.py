# Generated by Django 3.2.16 on 2023-02-03 04:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0014_add_new_permissions_for_roles'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mailinglist',
            name='access_level',
            field=models.CharField(default='members', max_length=32),
        ),
    ]
