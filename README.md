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

Bootstrapping a local Python development environment on your host machine for testing (make sure `USE_PYTHON_VERSION` corresponds to the current Python version used by the `Dockerfile`):

```sh
USE_PYTHON_VERSION="3.10.4"
VENV_DIR=".venv"
pyenv install --skip-existing ${USE_PYTHON_VERSION}
rm -Rf "${VENV_DIR}" && PYENV_VERSION=${USE_PYTHON_VERSION} python -m venv "${VENV_DIR}"
. "${VENV_DIR}"/bin/activate && pip install --upgrade pip wheel
. "${VENV_DIR}"/bin/activate && pip install -r lti_emailer/requirements/local.txt
```

Running it from your host machine, if libraries and a Python environment are installed locally:

```sh
ENV=dev DJANGO_SETTINGS_MODULE=lti_emailer.settings.local python manage.py runserver_plus --cert-file cert.crt
```