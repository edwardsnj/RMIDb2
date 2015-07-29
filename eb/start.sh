#!/bin/sh
DIRNAME=`dirname $0`
source $DIRNAME/config.sh                                                                                         
ENV="$NAME"
if ./stop.sh "$ENV"; then
  /tools/EPD/bin/eb create "$ENV" -c "$ENV" -s 
fi
