#!/bin/sh
DIRNAME=`dirname $0`
DIRNAME=`readlink -f $DIRNAME`
source $DIRNAME/config.sh                                                                                         
ENV="$NAME"
if /tools/EPD/bin/eb status "$ENV" 2>/dev/null 1>&2; then
   echo "$ENV" | /tools/EPD/bin/eb terminate "$ENV" || exit 1
fi
