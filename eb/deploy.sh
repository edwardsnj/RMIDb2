#!/bin/sh
DIRNAME=`dirname $0`
DIRNAME=`readlink -f $DIRNAME`
source $DIRNAME/config.sh                                                                                     
if [ ! -f prod.cfg ]; then
   echo "Please be in the root directory for rmidb2" 1>&2
   exit 1
fi
$DIRNAME/build.sh
cd $DIRNAME
$EB deploy
