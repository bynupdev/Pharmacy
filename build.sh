#!/bin/bash
# build.sh
# set -o errexit
# pip install -r requirements.txt
# python manage.py collectstatic --noinput
# python manage.py migrate --noinput

set -o errexit
cd src
pip install -r ../requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput