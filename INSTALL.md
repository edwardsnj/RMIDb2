
# Local installation

Required: Python 2.7 with numpy and scipy. A prepackaged distribution, such as
Enthought Python can simplify this process significantly. 

1. Unpack or checkout the rmidb2 distribution ($RMIDB2_HOME)

		unzip rmidb2.zip
		cd rmidb2
		export RMIDB2_HOME=`pwd`

2. Create a python container for RMIDb2 packages and modules.

		cd $RMIDB2_HOME
		virtualenv .python

3. Symbolic link python executable and numpy/scipy.

		cd $RMIDB2_HOME
		ln -s .python/bin/python
		cd .python/lib/python2.7/site-packages
		ln -s `python -c 'import numpy; print numpy.__path__[0]'`
		ln -s `python -c 'import scipy; print scipy.__path__[0]'`

4. Update and install the necessary python modules and packages.

		cd $RMIDB2_HOME
		.python/bin/pip install -U pip setuptools
		.python/bin/pip install -r req0.txt
		.python/bin/pip install -r req1.txt

5. Reinstate the .egg-info directory

		cd $RMIDB2_HOME
		./python setup.py egg-info

6. Initialize the SQLite3 database.

		cd $RMIDB2_HOME
		./python initdb.py

7. Start the RMIDb on localhost:8080.

		cd $RMIDB2_HOME
		./python start-rmidb2.py

# Elastic Beanstalk (AWS) Installation

Requires: Local installation as above. AWS credentials in $HOME/.aws/config.

1. Install Elastic Beanstalk command-line interface.

		cd $RMIDB2_HOME
		.python/bin/pip install awsebcli
		ln -s .python/bin/eb

2. Configure the EB parameters. The SMTPUSER, SMTPPASS, S3BUCKET
parameters can be left as is. Change the NAME paramter to something
reasonable.

		cd $RMIDB2_HOME
		cp eb/config.empty.sh eb/config.sh
		vi eb/config.sh

3. Initialize the eb directory for Elastic Beanstalk. Choose the Python
2.7 container and select the appropriate ssh key.

		cd $RMIDB2_HOME
		(cd eb; ./init.sh)

4. Build the web-application for Elastic Beanstalk.

		cd $RMIDB2_HOME
		./eb/build.sh

5. Start the RMIDb2 Elastic Beanstalk instance. Instance will be at $NAME.elasticbeanstalk.com.

		cd $RMIDB2_HOME
		./eb/start.sh

6. To update the RMIDb application without stopping the instance:

		cd $RMIDB2_HOME
		./eb/deploy.sh

6. To stop the RMIDb Elastic Beanstalk instance:

		cd $RMIDB2_HOME
		./eb/stop.sh

