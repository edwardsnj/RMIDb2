#!/bin/sh
DIRNAME=`dirname $0`
DIRNAME=`readlink -f $DIRNAME`
source $DIRNAME/config.sh                                                                                         
$EB logs
