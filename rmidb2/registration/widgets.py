from turbogears import widgets, validators, identity
from rmidb2.registration import model as register_model

class FakeInputWidget(widgets.Widget):
    "Simple widget that allows displaying its value in a span."
    
    params = ["field_class", "css_classes"]
    params_doc = {'field_class' : 'CSS class for the field',
                  'css_classes' : 'List of extra CSS classes for the field'}
    field_class = None
    css_classes = []
    
    def __init__(self, name=None, label=None, **kw):
        super(FakeInputWidget, self).__init__(name, **kw)
        self.label = label
        self.validator = None
        self.help_text = None
        
    template = """
        <span xmlns:py="http://genshi.edgewall.org/"
            class="${field_class}" 
            py:content="value" />
        """#"

class FakeInputWidgetWithLink(FakeInputWidget):
    "Simple widget that allows displaying its value in a span."
    
    template = """
        <span xmlns:py="http://genshi.edgewall.org/"
            class="${field_class}">${value[0]} (<A href="${value[2]}">${value[1]}</A>)</span> 
        """#"

class NewUserFields(widgets.WidgetsList):
    
    user_name = widgets.TextField('user_name',
                    label=_("User Name"),
                    help_text=_("A short name that you will use to log in."))
                    
    email = widgets.TextField('email',
                    label=_("Email"),
                    help_text=_("Your email address (this will be validated)."))
                    
    email_2 = widgets.TextField('email2',
                    label=_("Email (again)"),
                    help_text=_("Your email address again, please."))
    
    display_name = widgets.TextField('display_name',
                    label=_("Display Name"),
                    help_text=_("A longer user name that others will see."))
                    
    password_1 = widgets.PasswordField('password1',
                    label=_("Password"),
                    help_text=_("Your password."))
                    
    password_2 = widgets.PasswordField('password2',
                    label= _("Password (again)"),
                    help_text=_("Same password as above (the two should match)."))
                    
class ExistingUserFields(widgets.WidgetsList):
    
    user_name = FakeInputWidget('user_name',
                    label=_("User Name") )
                    
    email = widgets.TextField('email',
                    label=_("Email"),
                    help_text=_("Your email address (this will be validated)."))
    
    display_name = widgets.TextField('display_name',
                   label=_("Display Name"),
                   help_text=_("A longer user name that others will see."))
    
    old_password = widgets.PasswordField('old_password',
                   label=_("Current password"),
                   help_text=_("The current (old) password."))

    password_1 = widgets.PasswordField('password1',
                    label=_("New Password"),
                    help_text=_("Your new password. (If you would like to change it)."))

    password_2 = widgets.PasswordField('password2',
                    label=_("New Password (again)"),
                    help_text=_("New password again (should match the input above)."))

class SimpleSymbols(validators.Regex):
    regex = r"^[-a-zA-Z_0-9.]+$"
                    
class UniqueUsername(validators.FancyValidator):
    "Validator to confirm that a given user_name is unique."
    messages = {'notUnique': 'That user name is already being used.'}
    
    def _to_python(self, value, state):
        if not register_model.user_name_is_unique(value):
            raise validators.Invalid(self.message('notUnique', state), value, state)
        return value

class DeleteableUsername(validators.FancyValidator):
    "Validator to confirm that a given user_name can be deleted."
    messages = {'notDeleteable': 'That user name cannot be deleted.'}
    
    def _to_python(self, value, state):
        if register_model.user_name_is_unique(value):
            raise validators.Invalid(self.message('notDeleteable', state), value, state)
	elif value.strip() in ('admin','guest'):
	    raise validators.Invalid(self.message('notDeleteable', state), value, state)
        return value

class UniqueEmail(validators.FancyValidator):
    "Validator to confirm a given email address is unique."
    messages = {'notUnique': 'That email address is registered with an existing user.'}
    
    def _to_python(self, value, state):
        if identity.not_anonymous():
            if value == identity.current.user.email_address:
                # the user isn't trying to change their email address
                # so the value is ok
                return value 
        if not register_model.email_is_unique(value):
            raise validators.Invalid(self.message('notUnique', state), value, state)
        return value
        
class ValidPassword(validators.FancyValidator):
    """Validator to test for validity of password.
    """

    messages = {'invalid': 'The password you supplied is invalid.'}

    def validate_python(self, value, state):
        user = identity.current.user
        if not identity.current_provider.validate_password(user, user.user_name, value):
            raise validators.Invalid(
                self.message('invalid', state), value, state)
        return value
        
class NewUserSchema(validators.Schema):    
    user_name = validators.All(validators.UnicodeString(not_empty=True, 
                                                        max=16, strip=True),
                                UniqueUsername(),SimpleSymbols())
    email = validators.All(validators.Email(not_empty=True, max=255),
                                UniqueEmail())
    email2 = validators.All(validators.Email(not_empty=True, max=255))
    display_name = validators.UnicodeString(not_empty=True, strip=True, max=255)
    password1 = validators.String(not_empty=True, max=40)
    password2 = validators.String(not_empty=True, max=40)
    chained_validators = [validators.FieldsMatch('password1', 'password2'),
                            validators.FieldsMatch('email', 'email2')]
    
class ExistingUserSchema(validators.Schema):
    email = validators.All(validators.Email(not_empty=True, max=255),
                                UniqueEmail())
    display_name = validators.UnicodeString(not_empty=True, strip=True, max=255)
    old_password = validators.All(validators.String(max=40),
                                    ValidPassword())
    password1 = validators.String(max=40)
    password2 = validators.String(max=40)
    chained_validators = [validators.FieldsMatch('password1', 'password2')]
    
class RegTableForm(widgets.TableForm):
    template = 'rmidb2.templates.registration.tabletemplate'

lost_password_form = RegTableForm( fields = [
                                            widgets.TextField('email_or_username',
                                            label=_('User Name or Email Address'),
                                            validator=validators.UnicodeString(not_empty=True, max=255)) ]
                                        )
                                        
delete_user_form = RegTableForm(fields=[ widgets.TextField(name='user_name', label=_('User Name'), 
				         validator = validators.All(validators.UnicodeString(not_empty=True,
                                                                                             max=16, strip=True),
                                                                    DeleteableUsername(),SimpleSymbols())) ],
                                submit=widgets.SubmitButton(attrs=dict(onclick='return confirmDelete();')))
