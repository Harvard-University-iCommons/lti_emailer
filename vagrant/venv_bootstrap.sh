#!/bin/bash
export HOME=/home/vagrant
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv -a /home/vagrant/lti_emailer -r /home/vagrant/lti_emailer/lti_emailer/requirements/local.txt lti_emailer 
