
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

5. Initialize the SQLite3 database.

		cd $RMIDB2_HOME
		./python initdb.py

6. Start the RMIDb on localhost:8080.

		cd $RMIDB2_HOME
		./python start-rmidb2.py
