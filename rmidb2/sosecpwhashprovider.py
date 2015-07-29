from turbogears.identity.soprovider import *
from secpwhash import check_password

class SoSecPWHashIdentityProvider(SqlObjectIdentityProvider):

    def validate_password(self, user, user_name, password):
	# print >>sys.stderr, user, user.password, user_name, password
	return check_password(user.password,password)
