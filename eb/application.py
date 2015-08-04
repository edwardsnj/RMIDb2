import sys
sys.path.append('/opt/python/current/app')
sys.path.append('/usr/lib64/python2.7/dist-packages')
sys.path.append('/usr/lib/python2.7/dist-packages')
 
sys.stdout = sys.stderr
sys.argv = [ '', '/opt/python/current/app/rmidb2/config/prod.cfg' ]

import os
os.environ['PYTHON_EGG_CACHE'] = '/opt/python/current/app/python-eggs'

from rmidb2 import command, model
app = command.start()
# model.bootstrap_model()
# model.create_default_users()

import cherrypy._cpwsgi
application = cherrypy._cpwsgi.CPWSGIApp(app)
