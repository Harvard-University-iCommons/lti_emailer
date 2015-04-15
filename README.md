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
