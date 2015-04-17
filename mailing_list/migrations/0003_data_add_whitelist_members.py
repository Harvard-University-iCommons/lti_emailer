# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


email_whitelist = [
    'douglas_hall@harvard.edu',
    'hiukei_chow@harvard.edu',
    'josie_yip@harvard.edu',
    'sapna_mysore@harvard.edu',
    'eric_parker@harvard.edu',
    'elliott_yates@harvard.edu',
    'david_bonner@harvard.edu',
    'danny_brooke@harvard.edu',
    'david_downs@harvard.edu',
    'jill_ehrenzweig@harvard.edu',
    'kimberly_edelman@harvard.edu',
    'colin_murtaugh@harvard.edu',
    'roderick_morales@harvard.edu',
    'carter_snowden@harvard.edu',
    'chow_hiuk@yahoo.com',
    'tlttest101@gmail.com',
    'elliottyates@gmail.com'
]


def forwards(apps, schema_editor):
    # Create EmailWhitelist members
    EmailWhitelist = apps.get_model('mailing_list', 'EmailWhitelist')
    for address in email_whitelist:
        model = EmailWhitelist(email=address)
        model.save()


def backwards(apps, schema_editor):
    # Delete EmailWhitelist members
    EmailWhitelist = apps.get_model('mailing_list', 'EmailWhitelist')
    EmailWhitelist.objects.filter(email__in=email_whitelist).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('mailing_list', '0002_emailwhitelist'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards)
    ]
