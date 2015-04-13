#!/bin/bash
export HOME=/home/vagrant
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv -a /home/vagrant/icommons_lti_tools -r /home/vagrant/icommons_lti_tools/icommons_lti_tools/requirements/local.txt icommons_lti_tools 
