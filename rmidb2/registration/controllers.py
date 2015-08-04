import turbogears
import cherrypy
from turbogears import controllers, expose, redirect, url, widgets
from turbogears import identity, config, validate, error_handler
import pkg_resources
import logging
import datetime
import sha
import smtplib
import urllib
import string
import random
from email.MIMEText import MIMEText
from rmidb2.registration.widgets import NewUserFields, NewUserSchema, RegTableForm, \
        ExistingUserFields, ExistingUserSchema, lost_password_form, delete_user_form
from sqlobject import SQLObjectNotFound
from rmidb2.registration import model as register_model
try:
    import turbomail
except ImportError:
    turbomail = None
from registration.ormmanager import create, retrieve_one, delete

log = logging.getLogger('registration')

new_user_form = RegTableForm(fields=NewUserFields(), validator=NewUserSchema() )
                                    
edit_user_form = RegTableForm(fields=ExistingUserFields(), validator=ExistingUserSchema())

from turbogears.identity.conditions import Predicate, IdentityPredicateHelper

class not_guest(Predicate, IdentityPredicateHelper):
    """Predicate for checking whether current visitor is using the guest account."""
    error_message = "Guest access denied"

    def eval_with_object(self, identity, errors=None):
        if 'guest' in identity.groups:
            self.append_error_message(errors)
            return False
        return True

class is_admin(Predicate, IdentityPredicateHelper):
    """Predicate for checking whether current visitor is using the admin account."""
    error_message = "Admin access required"

    def eval_with_object(self, identity, errors=None):
        if 'admin' not in identity.groups:
            self.append_error_message(errors)
            return False
        return True

class UserRegistration(controllers.Controller):

    def __init__(self):
        super(UserRegistration, self).__init__()
        random.seed()
        self.hash_salt = ''.join([random.choice(string.printable) for i in range(20)])
        self.smtp_server = config.get('registration.mail.smtp_server', 'localhost')
        self.smtp_port = config.get('registration.mail.smtp_server_port', 25)
        self.smtp_username = config.get('registration.mail.smtp_server.username', None)
        self.smtp_pw = config.get('registration.mail.smtp_server.password', None)
    
    @expose()
    def index(self):
        if identity.current.anonymous or identity.current.user_name == 'guest':
            redirect('new')
        else:
            redirect('edit')
            
    @expose(template='rmidb2.templates.registration.new')
    def new(self, tg_errors=None):
        if not identity.current.anonymous and not identity.current.user_name == 'guest':
            redirect('/registration/edit')
        if tg_errors:
            turbogears.flash(_('There was a problem with the data submitted.'))
        return dict(form=new_user_form, action='./create', 
                    submit_text=_('Create Account'))
        
    @expose(template='rmidb2.templates.registration.create')
    @validate(form=new_user_form)
    @error_handler(new)
    def create(self, user_name, email, email2, display_name, password1, password2):
        if not identity.current.anonymous and not identity.current.user.is_guest():
            redirect('/registration/edit')
        key = self.validation_hash(email + display_name + password1)
        pend = create(register_model.RegistrationPendingUser,
                                user_name=user_name,
                                email_address=email,
                                display_name=display_name,
                                password=password1,
                                validation_key=key
                                )  
        error_msg = None
        try:
            self.mail_new_validation_email(pend)
        except smtplib.SMTPRecipientsRefused, args:
            # catch SMTP error before they can bite
            error_code, error_message = args[0][pend.email_address]
            
            if error_code == 450:
                # SMTP refused either sender or receiver
                error_msg = _('Your email was refused with error: %s' % error_message)
            else:
                # some other error code ?
                error_msg = '%s' % error_message
    
        if config.get('registration.unverified_user.groups') and not error_msg:
            # we have unverified_user.groups.  Add the user to the User table
            # and add the appropriate groups
            user = self.promote_pending_user(pend)
            self.add_unverified_groups(user)
            # log them in
            # i = identity.current_provider.validate_identity(user_name, password1, 
            #                                                 identity.current.visit_key)
            # identity.set_current_identity(i)
        return dict(name=display_name, email=email, error_msg=error_msg)
        
    @expose(template='rmidb2.templates.registration.validate')
    def validate_new_user(self, email='', key=''):
        is_valid = False
        pend = retrieve_one(register_model.RegistrationPendingUser, 
                            email_address=email)
        if pend and pend.validation_key == key:
            is_valid = True
        if not is_valid:
            if identity.current.user:  
                #This is probably just someone with an old/stale link
                redirect('edit')
            log.info('%s Bad validation using email=%s validation_key=%s' % 
                        (cherrypy.request.remote.ip, email, key))
            return dict(is_valid=is_valid, 
                        admin_email=config.get('registration.mail.admin_email',
                            ''))
        else:
            if config.get('registration.unverified_user.groups'):
                # The pending user is already in the Users table
                new_user = retrieve_one(register_model.User, email_address=email)
                self.remove_all_groups(new_user)
            else:
                # Add the pending user to the Users table
                new_user = self.promote_pending_user(pend)
            
            self.add_standard_groups(new_user)
            delete(pend)
            # If you have a protected url that a basic user can log into and see, 
            # set it as login_url (instead of identity.failure_url).  
            # Otherwise, the user will loop back to validate after logging in, and then over 
            # to /.
            login_url = url(config.get('identity.failure_url'))
            return dict(name=getattr(new_user, 'display_name', new_user.user_name), 
                        login=login_url, 
                        is_valid=is_valid)
            
    def promote_pending_user(self, pending_user):
        """Copies a pending user from pending and into the official 'users'.
        
        Returns the new user object.
        """
        # Let's try to do this programmatically.  The only thing you should have to modify 
        # if you changed the schema fo RegistrationPendingUser is the 'excluded' list.  All 
        # columns not in this list will be mapped straight to a new user object.
        
        # This list contains the columns from RegistrationPendingUser that you DON'T want 
        # to migrate
        excluded = ['created', 'validation_key']
        columns = pending_user.sqlmeta.columns.keys()
        new_columns = dict()
        for c in columns:
            if c not in excluded:
                new_columns[c] = getattr(pending_user, c)
        u = create(register_model.User, **new_columns)
	u.set_password_raw(pending_user.password)
	return u

    def mail_new_validation_email(self, pending_user):
        "Generate the new user validation email."
        reg_base_url = self.registration_base_url()
        queryargs = urllib.urlencode(dict(email=pending_user.email_address, 
                                          key=pending_user.validation_key))
        url = '%s/validate_new_user?%s' % (reg_base_url, queryargs)
        
        body = pkg_resources.resource_string('rmidb2', 
                        'templates/registration/email_body_new.txt')
        
        self.send_email(pending_user.email_address, 
                        config.get('registration.mail.admin_email', 'admin@localhost'), 
                        config.get('registration.mail.new.subject', 'New User Registration'), 
                        body % {'validation_url': url})
     
    @expose(template='rmidb2.templates.registration.lost_password')
    def lost_password(self, tg_errors=None):
        "Show the lost password form."
        if not identity.current.anonymous and not identity.current.user.is_guest():
            redirect('edit')
        policy = config.get('registration.lost_password_policy', 'send_current')
        return dict(policy=policy, form=lost_password_form, 
                    action="recover_lost_password")
        

    @expose(template="rmidb2.templates.registration.recover_lost_password")
    @validate(form=lost_password_form)
    @error_handler(lost_password)
    def recover_lost_password(self, email_or_username=None):
        "Resets (or mails) a user's forgotten password."
        if not identity.current.anonymous and not identity.current.user.is_guest():
            redirect('edit')
        reset_password = user = user_email = None
        User = register_model.User
        user = retrieve_one(User, email_address=email_or_username)
        if not user:
            user = retrieve_one(User, user_name=email_or_username)
        policy = config.get('registration.lost_password_policy', 'send_current')
        enc_alg = config.get('identity.soprovider.encryption_algorithm', None)

        # We can't send the password if it is encrypted; must reset.
        if user and (enc_alg or (policy == 'reset')):
            # generate a new password for the user
            chars = string.ascii_letters + string.digits
            random.seed()
            new_pw = ''
            # Compose a new random password  6-9 chars long
            for i in range(0, random.choice((6, 7, 8, 9))):
                new_pw = '%s%s' % (new_pw, random.choice(chars))
            user.password = new_pw

            body = pkg_resources.resource_string('rmidb2', 
                        'templates/registration/email_body_reset_password.txt')
            self.send_email(user.email_address, 
                            config.get('registration.mail.admin_email', 'admin@localhost'), 
                            config.get('registration.mail.lost_password.subject', "Password Request"),
                            body % {'password': new_pw, 'user_name': user.user_name})
            user_email = user.email_address
            reset_password = True
        elif user:  # sending the current password
            body = pkg_resources.resource_string('rmidb2', 
                        'templates/registration/email_body_lost_password.txt')
            self.send_email(user.email_address,
                            config.get('registration.mail.admin_email'), 
                            config.get('registration.mail.lost_password.subject',
                                        "Password Request"),
                            body % {'password': user.password, 
                                    'user_name': user.user_name})
            user_email = user.email_address

        return dict(email=user_email, reset_password=reset_password)
        
    @expose(template='rmidb2.templates.registration.edit_user')
    @identity.require(identity.All(identity.not_anonymous(),
				   not_guest()))
    def edit(self, tg_errors=None):
        "Edit current user information."
        u = identity.current.user
        form_values = dict(user_name=u.user_name, email=u.email_address, 
                           old_password='',
                           password_1='', password_2='',display_name=u.display_name)
        return dict(form=edit_user_form, 
                    form_values=form_values, 
                    action="update_user")

    @expose()
    @identity.require(identity.All(identity.not_anonymous(),
                                   not_guest()))
    @validate(form=edit_user_form)
    @error_handler(edit)                
    def update_user(self, email, display_name, old_password, password1, password2, user_name=None):
        "Updates the users information with new values."
        user = identity.current.user
        msg = ""
        if password1:
            user.password=password1
            msg = _("Your password was changed. ")
        if display_name != user.display_name:
            user.display_name = display_name
            msg = _("Your display name was changed. ")
        if email and email != user.email_address:
            try:
                self.mail_changed_email_validation(email)
                msg = msg + _("You will recieve an email at %s with instructions to complete changing your email address." % email)
            except smtplib.SMTPRecipientsRefused, args:
                msg = _("The provided new email was refused by our server, please provide a valid email.")

        turbogears.flash(msg)
        redirect('edit')
        
    def mail_changed_email_validation(self, new_email):
        """Sends an email out that has validation information for changed email addresses.
        
        The logic is that we keep the old (verified) email in the User table, and add the
        new information into the RegistrationUserEmailChange table.  When the user eventually
        validates the new address, we delete the information out of RegistrationUserEmailChange 
        and put the new email address into User table.  That way, we always have a "good" email 
        address in the User table.
        """
        unique_str = new_email + identity.current.user.email_address
        validation_key = self.validation_hash(unique_str)
        email_change = create(register_model.RegistrationUserEmailChange,
                    user=identity.current.user,
                    new_email_address=new_email,
                    validation_key=validation_key)                                           
        reg_base_url = self.registration_base_url()
        queryargs = urllib.urlencode(dict(email=new_email, 
                                          key=validation_key))
        url = '%s/validate_email_change?%s' % (reg_base_url, queryargs)
                                            
        body = pkg_resources.resource_string('rmidb2', 
                                    'templates/registration/changed_email.txt')
        self.send_email(new_email,
                    config.get('registration.mail.admin_email', 'admin@localhost'), 
                    config.get('registration.mail.changed_email.subject', 
                                'Please verify your new email address'),
                    body % {'validation_url': url})
    
    @expose(template='rmidb2.templates.registration.validate_email')
    def validate_email_change(self, email, key):
        "Validate the email address change and update the database appropriately."
        is_valid = False
        admin_email = config.get('registration.mail.admin_email')
        email_change = retrieve_one(register_model.RegistrationUserEmailChange, 
                                new_email_address=email)
        if not email_change:
            return dict(is_valid=False, admin_email=admin_email)
        if email_change.validation_key == key:
            is_valid = True
            user = email_change.user
            # change the user's email address and delete the email_change record
            user.email_address = email
            delete(email_change)
        return dict(is_valid=is_valid, 
                    email=email, 
                    name=user.display_name,
                    admin_email=admin_email)
    
    @expose(template='rmidb2.templates.registration.delete_user')
    @identity.require(is_admin())
    def delete_user(self):
        "Remove a user from the application."
        confirm_msg = _("The account will be immediately and permanently\\n"
                        "deleted.\\n\\nAre you sure you wish to continue?")
        return dict(form=delete_user_form, 
                    confirm_msg=confirm_msg, 
                    submit_text=_('Submit'),
                    action='do_delete')
    
    @expose()
    @identity.require(is_admin())
    @validate(form=delete_user_form)
    @error_handler(delete_user)                
    def do_delete(self, user_name):
        "Do the work of deleting a user."
        # The form does the password validation; so we know the user has already
        # given us a valid password.  All that is left to do is delete the user.
        # If you have other cleanup or logging items that need to be done when 
        # a user is deleted, this is the place to do them. 
	user = register_model.User.by_user_name(user_name)
        delete(user)
	user.destroySelf()
        redirect('/')
        
    def add_standard_groups(self, user):
        "Add the user to the groups specified in the config file."
        self.add_groups(user, config.get('registration.verified_user.groups', []))
    
    def add_unverified_groups(self, user):
        "Adds the user to the unverified user groups specified in the config file."
        self.add_groups(user, config.get('registration.unverified_user.groups', []))
        
    def add_groups(self, user, group_list):
        "Adds the user to each of the groups in the group_list sequence."
        group_join = self.get_group_join(user)
        try:
            add_group_method = getattr(user, 'addGroup')
        except AttributeError:
            add_group_method = getattr('add' + group_join.addRemoveName)
        if not add_group_method:
            # If we ever get to here, we need to program the proper group join
            # method.
            raise ValueError("Can't find the proper method to add a group.")
        for group_name in group_list:
            group = group_join.otherClass.by_group_name(group_name) # Find the group
            add_group_method(group)   # add user to the group
            
    def remove_all_groups(self, user):
        "Removes the user from all groups that a User belongs to."
        group_join = self.get_group_join(user)
        try: 
            remove_group_method = getattr(user, 'removeGroup')
        except AttributeError:
            remove_group_method = getattr('remove' + group_join.addRemoveName)
        if not remove_group_method:
            raise ValueError("Can't find the proper method to remove a group")
        for group in getattr(user, group_join.joinMethodName):
            remove_group_method(group)
        
        
    def get_group_join(self, user):
        # Try to find the join column from user to group.
        # assume it is the only one that contains the word 'group'
        for join in user.sqlmeta.joins:
            if join.joinMethodName.lower().find('group') != -1:
                return join
        raise ValueError("Can't find the proper group join.")
        

    def validation_hash(self, unique_input=""):
        "Returns a hash that can be used for validation."
        hash_str =  u" ".join((unique_input, cherrypy.request.remote.ip, 
                             self.hash_salt, datetime.datetime.now().isoformat()))
        return sha.new(unicode(hash_str).encode('ascii', 'replace')).hexdigest()
        
    def registration_base_url(self):
        """Returns the full http://... address of the registration controller.
        
        Does not end with a traling slash.
        """
        # Trying to find the path to the main registration controller.
        # If this has trouble, you may need to hardcode the return value
        # for this function
        last_slash = cherrypy.request.path_info.rfind('/')
        path = cherrypy.request.path_info[:last_slash]
        return '%s%s' % (cherrypy.request.base, path)
	# return '/registration'
        
    def send_email(self, to_addr, from_addr, subject, body):
        """Send an email.
        """
        # Using turbomail if it exists, 'dumb' method otherwise
        if turbomail and config.get('mail.on'):
            msg = turbomail.Message(from_addr, to_addr, subject)
            msg.plain = body
            turbomail.enqueue(msg)
        else:
            msg = MIMEText (body)
            msg['Subject'] = subject
            msg['From'] = from_addr
            msg['To'] = to_addr
        
            smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.smtp_username:
                smtp.login(self.smtp_username, self.smtp_pw)
            smtp.sendmail(from_addr, to_addr, msg.as_string())
            smtp.quit()
