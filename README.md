# LTI Emailer

This project provides an LTI tool for working with email in the context of a Canvas course.

## Mailing List

The mailing list app provides an interface for creating and using mailing list email addresses for each section
within a Canvas course. Mailing lists can be configured to allow only teaching staff to post to the list, only
section enrollees to post to the list, anyone to post to the list, or no one to post to the list.

## Implementation Details

The models defined within this project can be configured to use any standard database (postgresql,
Sqlite, Oracle).

A distributed cache is used to cache mailing list data (currently configured to use Redis).

We use the [Mailgun API](https://documentation.mailgun.com/ "Mailgun API") to send/receive email to/from users.

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
allowing the connection.

And because it accesses the coursemanager, don't forget the VPN.
