#!/bin/sh
DIRNAME=`dirname $0`
source $DIRNAME/config.sh                                                                                         
$EB init "$NAME" --region "$REGION"
