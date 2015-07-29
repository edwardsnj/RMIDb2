#!/bin/sh
DIRNAME=`dirname $0`
source $DIRNAME/config.sh                                                                                         
if [ ! -f prod.cfg ]; then
   echo "Please be in the root directory for rmidb2" 1>&2
   exit 1
fi
if [ -d build ]; then
    rm -rf build
fi
rm -rf $DIRNAME/rmidb2
./python setup.py build
cp -r build/lib/rmidb2 $DIRNAME
cp prod.cfg $DIRNAME/rmidb2/config
rm -rf build
