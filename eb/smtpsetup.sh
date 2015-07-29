#!/bin/sh
DIRNAME=`dirname $0`
source $DIRNAME/config.sh                                                                                         

# Presume we've already run...
if [ -f $MAILDIR/authinfo ]; then
  exit 0
fi

# Add file authinfo
cat <<EOF1 >$MAILDIR/authinfo
AuthInfo:$SMTPHOST "U:root" "I:$SMTPUSER" "P:$SMTPPASS" "M:LOGIN PLAIN"
EOF1
makemap hash $MAILDIR/authinfo.db < $MAILDIR/authinfo

# Add line to end of $MAILDIR/access
cat <<EOF2 >>$MAILDIR/access
Connect:$SMTPHOST RELAY
EOF2
makemap hash $MAILDIR/access.db < $MAILDIR/access

# Insert text into $MAILDIR/sendmail.mc before that last three lines
head -n -3 $MAILDIR/sendmail.mc > $MAILDIR/sendmail.mc.new
echo >> $MAILDIR/sendmail.mc.new
echo -n 'define(`SMART_HOST'\'', `' >> $MAILDIR/sendmail.mc.new
echo "$SMTPHOST')dnl" >> $MAILDIR/sendmail.mc.new

cat <<'EOF3' >>$MAILDIR/sendmail.mc.new
define(`RELAY_MAILER_ARGS', `TCP $h 25')dnl
define(`confAUTH_MECHANISMS', `LOGIN PLAIN')dnl
EOF3
echo -n 'FEATURE(`authinfo'\'', `hash -o ' >>$MAILDIR/sendmail.mc.new
echo "$MAILDIR/authinfo.db')dnl" >>$MAILDIR/sendmail.mc.new
echo -n 'MASQUERADE_AS(`' >>$MAILDIR/sendmail.mc.new
echo "$DOMAIN')dnl" >>$MAILDIR/sendmail.mc.new
cat <<'EOF3' >>$MAILDIR/sendmail.mc.new
FEATURE(masquerade_envelope)dnl
FEATURE(masquerade_entire_domain)dnl

EOF3
tail -n 3 $MAILDIR/sendmail.mc >> $MAILDIR/sendmail.mc.new
mv -f $MAILDIR/sendmail.mc $MAILDIR/sendmail.mc.bak
mv -f $MAILDIR/sendmail.mc.new $MAILDIR/sendmail.mc
if [ -f $MAILDIR/sendmail.cf ]; then
  chmod 666 $MAILDIR/sendmail.cf
fi
m4 $MAILDIR/sendmail.mc > $MAILDIR/sendmail.cf
chmod 644 $MAILDIR/sendmail.cf
/etc/init.d/sendmail restart
