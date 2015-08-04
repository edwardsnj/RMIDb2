import sys
sys.path.append('/opt/python/ondeck/app')
sys.path.append('/usr/lib64/python2.7/dist-packages')
sys.path.append('/usr/lib/python2.7/dist-packages')

import turbogears
from rmidb2 import model
turbogears.update_config(configfile="rmidb2/config/prod.cfg", 
                         modulename="rmidb2.config")
model.bootstrap_model()
model.create_default_users()

