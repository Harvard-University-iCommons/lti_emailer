# LTI Emailer

This project provides an LTI tool for working with email in the context of a Canvas course.

## Mailing List

The mailing list app provides an interface for creating and using listserv mailing lists for each section
within a Canvas course. The listserv mailing lists are kept in sync with the section enrollments
via an asynchronous job that runs on a schedule. Mailing lists can be configured to allow only section enrollees
to post to the list, anyone to post to the list, or no one to post to the list.

## Implementation Details

This application currently needs a coursemanager database configuration in order to look up course enrollee
emails. The models defined within this project can be configured to use any standard database (postgresql,
Sqlite, Oracle).

A distributed cache is used to cache mailing list data (currently configured to use Redis).

[Mailgun](https://documentation.mailgun.com/) is currently the mail/listserv provider for this application.

The asynchronous listserv sync job is currently implemented using [Huey](https://github.com/coleifer/huey).
After deployment, a huey worker must be started by running `python manage.py run_huey`.  Note that because a
periodic task is defined for this application, only a single huey worker should be run.  Otherwise, that
periodic task will run once per worker.

## Local dev setup

After getting all your db connection stuff setup in the secure.py, access the 
vagrant shell and bring up the postgres shell via `psql`. At the shell prompt:
    alter role vagrant with password '(your secure.py default db password)';

Then, back in the vagrant shell:
    python manage.py init_db
    python manage.py migrate

If you're running via runsslserver and testing in Chrome, you'll need to 'bless'
the local SSL connection in Chrome by first bringing up the tool_config
(e.g. `https://localhost:8000/tool_config`) in a separate window and explicitly
allowing the connection)

And because it accesses the coursemanager, don't forget the VPN.
