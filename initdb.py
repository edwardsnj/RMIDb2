import sys

import turbogears
from rmidb2 import model
turbogears.update_config(configfile="dev.cfg", 
                         modulename="rmidb2.config")
model.bootstrap_model()
model.create_default_users()

