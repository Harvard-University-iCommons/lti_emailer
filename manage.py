#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    if 'test' in sys.argv:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'lti_emailer.settings.unit_test'
    else:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lti_emailer.settings.aws')

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
