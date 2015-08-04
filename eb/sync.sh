#!/bin/sh
DIRNAME=`dirname $0`
DIRNAME=`readlink -f $DIRNAME`
source $DIRNAME/config.sh                                                                                         
function asdaemon {
  while true; do
    if [ -d /opt/python/current/app ]; then
      cd /opt/python/current/app
      mkdir -p synctos3
      cd synctos3
      if [ -s ../server.log ]; then
        DATE=`date "+%Y%m%d%H%M"`
        cp ../devdata.sqlite devdata.sqlite.$DATE
        cp ../server.log server.log.$DATE
	if [ -f server.log ]; then
	  rm -f server.log
        fi
        ln -s server.log.$DATE server.log
	if [ -f devdata.sqlite ]; then
	  rm -f devdata.sqlite
        fi
        ln -s devdata.sqlite.$DATE devdata.sqlite
        rm -f `ls -rt server.log.* | head -n -5`
        rm -f `ls -rt devdata.sqlite.* | head -n -5`
        aws s3 sync --delete ./ $S3BUCKET/$NAME
      fi
    fi
    sleep 300
  done
}
kill -9 `ps -ef | fgrep sync.sh | fgrep root | awk '$3 == 1 {print $2}'`
asdaemon </dev/null >/dev/null 2>&1 &
