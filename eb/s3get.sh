#!/bin/sh
DIRNAME=`dirname $0`
DIRNAME=`readlink -f $DIRNAME`
source $DIRNAME/config.sh                                                                                         
if [ ! -f /opt/python/ondeck/app/devdata.sqlite ]; then
  if [ `aws s3 ls $S3BUCKET/$NAME/devdata.sqlite | wc -l` -gt 0 ]; then
    aws s3 cp $S3BUCKET/$NAME/devdata.sqlite /opt/python/ondeck/app
    chown wsgi:wsgi /opt/python/ondeck/app/devdata.sqlite
    chmod u+w /opt/python/ondeck/app/devdata.sqlite
  fi
fi
