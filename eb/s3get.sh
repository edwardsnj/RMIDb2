#!/bin/sh
DIRNAME=`dirname $0`
source $DIRNAME/config.sh                                                                                         
if [ ! -f /opt/python/ondeck/app/devdata.sqlite ]; then
  if [ `aws s3 ls s3://$S3BUCKET/state/$NAME/devdata.sqlite | wc -l` -gt 0 ]; then
    aws s3 cp s3://$S3BUCKET/state/$NAME/devdata.sqlite /opt/python/ondeck/app
    chown wsgi:wsgi /opt/python/ondeck/app/devdata.sqlite
    chmod u+w /opt/python/ondeck/app/devdata.sqlite
  fi
fi
