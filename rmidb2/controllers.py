# -*- coding: utf-8 -*-
"""This module contains the controller classes of the application."""

# symbols which are imported by "from rmidb2.controllers import *"
__all__ = ['Root']

# standard library imports
import os.path
# import logging

# log = logging.getLogger('rmidb2.controllers')

# third-party imports
from cherrypy import request
from sqlobject import SQLObjectNotFound, AND
from turbogears import controllers, expose, identity, redirect, visit, paginate
from turbogears import widgets, error_handler, validators, validate
from turbogears.toolbox.catwalk import CatWalk
import threading, datetime

# project specific imports
from registration import controllers as reg_controllers
from rmidb2.model import VisitIdentity
from async import *


# logging in after successfully registering a new user
def login_user(user):
    """Associate given user with current visit & identity."""
    visit_key = visit.current().key
    try:
        link = VisitIdentity.by_visit_key(visit_key)
    except SQLObjectNotFound:
        link = None

    if not link:
        link = VisitIdentity(visit_key=visit_key, user_id=user.id)
    else:
        link.user_id = user.user_id

    user_identity = identity.current_provider.load_identity(visit_key)
    identity.set_current_identity(user_identity)


# Customer Classes
class RegistrationFields(widgets.WidgetsList):
    displayName = widgets.TextField(label="Display Name:",attrs=dict(size=50))
    userName = widgets.TextField(label="Username:",attrs=dict(style="width: 100%;"))
    password = widgets.PasswordField(label="Password:",attrs=dict(style="width: 100%;"))
    confirmPassword = widgets.PasswordField(label="Re-enter Password:",attrs=dict(style="width: 100%;"))

class UniqueUsername(validators.FancyValidator):
    "Validator to confirm that a given user_name is unique."
    messages = {'notUnique': 'That user name is already being used.'}
    
    def _to_python(self, value, state):
	try:
            u = model.User.by_user_name(value)
            raise validators.Invalid(self.message('notUnique', state), value, state)
	except model.SQLObjectNotFound:
	    pass
        return value

class RegistrationFieldsSchema(validators.Schema):
    userName = validators.All(validators.UnicodeString(max=16, not_empty=True, strip=True),
			      UniqueUsername())
    password = validators.UnicodeString(min=5, max=40, not_empty=True, strip=True)
    confirmPassword = validators.UnicodeString(min=5, max=40, not_empty=True, strip=True)
    displayName = validators.UnicodeString(not_empty=True, strip=True)
    chained_validators = [validators.FieldsMatch('password', 'confirmPassword')]

class SearchFields(widgets.WidgetsList):
    title = widgets.TextField(label="Title:",attrs=dict(style="width: 100%;"))
    query = widgets.TextArea(label="Peaks:",attrs=dict(style="width: 100%;"))
    minMass = widgets.TextField(label="Min. Mol. Weight:",default=4000.0,attrs=dict(style="width:100%;"))
    maxMass = widgets.TextField(label="Max. Mol. Weight:",default=15000.0,attrs=dict(style="width:100%;"),css_classes=['aside'])
    massTolerance = widgets.TextField(label="Mass Tolerance (Da):",default=3.0,attrs=dict(style="width:100%;"))
    specMode = widgets.SingleSelectField(label="Ionization Mode:", options=["Positive", "Negative"],
                                         default="Positive",attrs=dict(style="width: 100%;"))
    # database = widgets.SingleSelectField(label="Databases"
                                         # options=["Ribosomal Proteins in Bacteria: Unreviewed",
                                                  # "Ribosomal Proteins in Bacteria: Reviewed"],
                                         # default="Ribosomal Proteins in Bacteria: Reviewed")
    database = widgets.HiddenField(default="Ribosomal Proteins in Bacteria: Reviewed")

class OneOrMoreNumbers(validators.FancyValidator):
    messages = {'notNumbers': 'Please enter a space separated list of positive numbers.'}
    
    def _to_python(self, value, state):
	try:
            numbers = map(float,value.split())
	    for n in numbers:
		if not n > 0:
		    raise validators.Invalid(self.message('notNumbers', state), value, state)
		elif not n < 1e+20:
		    raise validators.Invalid(self.message('notNumbers', state), value, state)
	except ValueError:
            raise validators.Invalid(self.message('notNumbers', state), value, state)
        return value

class SearchFieldsSchema(validators.Schema):
    title = validators.UnicodeString(not_empty=True, strip=True)
    query = validators.All(validators.UnicodeString(not_empty=True, strip=True),
		           OneOrMoreNumbers())
    maxMass = validators.Number(not_empty=True, strip=True)
    minMass = validators.Number(not_empty=True, strip=True)
    massTolerance = validators.Number(not_empty=True, strip=True)
    specMode = validators.OneOf(["Positive", "Negative"])
    database = validators.OneOf(["Ribosomal Proteins in Bacteria: Unreviewed",
                                 "Ribosomal Proteins in Bacteria: Reviewed"])


registrationForm = widgets.TableForm(
    fields=RegistrationFields(),
    validator=RegistrationFieldsSchema(),
    action="signupsubmit",
    submit_text="Register"
)

engineForm = widgets.TableForm(
    fields=SearchFields(),
    validator=SearchFieldsSchema(),
    action="searchsubmit",
    submit_text="Search",
    table_attrs=dict()
)

class Root(controllers.RootController):
    catwalk = CatWalk(model)
    catwalk = identity.SecureObject(catwalk, identity.in_group('admin'))

    registration = reg_controllers.UserRegistration()

    @expose('rmidb2.templates.index')
    def index(self):
	if not identity.current.anonymous:
	    raise redirect('/searchlist')
        siteTitle = "RMIDb: Home"
        return dict(siteTitle=siteTitle)

    @expose('rmidb2.templates.about')
    def about(self):
        siteTitle = "RMIDb: About"
        directory = os.path.dirname(__file__)
        with open(directory+'/static/text/references.txt', 'r') as ReferenceContent:
            ref = ReferenceContent.read().strip().split("\n")
        return dict(siteTitle=siteTitle,ref=ref)

    @expose('rmidb2.templates.contact')
    def contact(self):
        authors = [
            {"name": "Mingda Jin",
             "email": "mj568@georgetown.edu"},
            {"name": "Nathan Edwards",
             "email": "nje5@georgetown.edu"}
        ]
        siteTitle = "RMIDb: Contact"
        return dict(contacts=authors, siteTitle=siteTitle)

    @expose('rmidb2.templates.login')
    def login(self, forward_url=None, *args, **kw):
        """Show the login form or forward user to previously requested page."""

        if forward_url:
            if isinstance(forward_url, list):
                forward_url = forward_url.pop(0)
            else:
                del request.params['forward_url']

        new_visit = visit.current()
        if new_visit:
            new_visit = new_visit.is_new

        if (not new_visit and not identity.current.anonymous
                and identity.was_login_attempted()
		and identity.in_group("validated")
                and not identity.get_identity_errors()):
            # Redirection
	    identity.current.user.last_login = datetime.now()
            redirect(forward_url or '/searchlist', kw)

        if identity.was_login_attempted():
            if new_visit:
                msg = _(u"Cannot log in because your browser "
                         "does not support session cookies.")
            else:
                if not identity.in_group("validated"):
                    msg = _(u"The credentials you suppplied have not been "
                             "verified. Please verify using the URL in "
                             "your New User Registration email.")
                    identity.current.logout()
		else:
                    msg = _(u"The credentials you supplied were not correct or "
                             "did not grant access to this resource.")
        elif identity.get_identity_errors():
            msg = _(u"You must provide your credentials before accessing "
                     "this resource.")
        else:
            msg = _(u"Please log in.")
            # msg = _(u"")
            if not forward_url:
                forward_url = request.headers.get('Referer', '/')

        # we do not set the response status here anymore since it
        # is now handled in the identity exception.
        return dict(logging_in=True, message=msg,
            forward_url=forward_url, previous_url=request.path_info,
            original_parameters=request.params)

    @expose()
    @identity.require(identity.not_anonymous())
    def logout(self):
        """Log out the current identity and redirect to start page."""
        identity.current.logout()
        redirect('/')

    @expose('rmidb2.templates.signupForm')
    def signup(self):
        siteTitle = "RMIDb: Register"
        return dict(siteTitle=siteTitle, form=registrationForm)

    @expose()
    @validate(form=registrationForm)
    @error_handler(signup)
    def signupsubmit(self, **kw):
        # Create a user
	try:
            u = model.User(user_name=kw['userName'], password=kw['password'], 
	                   display_name=kw['displayName'])
	except DuplicateEntryError:
	    raise 
        login_user(u)
        redirect('/')

    @expose()
    def guest(self):
	u = model.User.by_user_name('guest')
	login_user(u)
	identity.current.user.last_login = datetime.now()
	redirect('/')

    @expose('rmidb2.templates.signupConfirmation')
    def signupconfirmation(self):
        siteTitle = "RMIDb: Welcome"
        return dict(siteTitle=siteTitle)

    @expose('rmidb2.templates.searchForm')
    @identity.require(identity.not_anonymous())
    def search(self, **kw):
        siteTitle = "RMIDb: New Search"
        user = identity.current.user
        if user.is_admin():
            user = model.User.by_user_name('guest')
        previousSearches = model.SearchList.select(AND(model.SearchList.q.status != model.DELETED,
                                                       model.SearchList.q.user == user),
						   orderBy='-created')[:5]
        return dict(siteTitle=siteTitle, form=engineForm, values=kw, searchHistory=previousSearches)

    @expose()
    @identity.require(identity.not_anonymous())
    @validate(form=engineForm)
    @error_handler(search)
    def searchsubmit(self, **kw):
        user = identity.current.user
        if user.is_admin():
            user = model.User.by_user_name('guest')
        model.SearchList(title=kw['title'], min_mass=kw['minMass'], max_mass=kw['maxMass'],
                         query=kw['query'], mass_tolerance=kw['massTolerance'], spec_mode=kw['specMode'],
                         database=kw['database'], user=user)

        # Start the search thread immediately
        t = threading.Thread(target=MicroorganismIdentification)
        t.daemon = True
        t.start()

        redirect('/searchlist')

    @expose('rmidb2.templates.searchList')
    @identity.require(identity.not_anonymous())
    @paginate('searchData', default_order="-created")
    def searchlist(self):
        user = identity.current.user
        if user.is_admin():
            user = model.User.by_user_name('guest')
        userSearch = model.SearchList.select(AND(model.SearchList.q.status != model.DELETED,
						 model.SearchList.q.user == user))
        ordinal = dict(map(lambda t: (t[1].id,t[0]),enumerate(model.SearchList.select(model.SearchList.q.status == model.QUEUED,orderBy='id'))))
        siteTitle = "RMIDb: Search List"
        return dict(siteTitle=siteTitle, searchData=userSearch,ordinal=ordinal)

    @expose()
    @identity.require(identity.not_anonymous())
    def searchdelete(self, id):
        #print searchID
        #print "@" * 100
        #model.SearchList.deleteBy(searchID)
	s = model.SearchList.get(id)
	if (s.user == identity.current.user or identity.current.user.is_admin()) \
               and s.status != model.RUNNING:
	    s.status = model.DELETED
        redirect('/searchlist')

    @expose('rmidb2.templates.searchResult')
    @identity.require(identity.not_anonymous())
    @paginate('resultData', default_order="p_value")
    def searchresult(self, searchID):
        s = model.SearchList.get(searchID)
        if s.user == identity.current.user or identity.current.user.is_admin():
            r = s.results
            return dict(resultData=r,search=s)
        redirect('/searchlist')

    @expose('rmidb2.templates.searchResultMatch')
    @identity.require(identity.not_anonymous())
    @paginate('matchData', default_order="peak")
    def searchresultmatch(self, resultID):
        r = model.ResultList.get(resultID)
        if r.search.user == identity.current.user or identity.current.user.is_admin():
            m = r.matches
            return dict(matchData=m,result=r)
        redirect('/searchresult?searchID=%d'%r.search.id)

