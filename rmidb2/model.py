# -*- coding: utf-8 -*-
"""This module contains the data model of the application."""

# symbols which are imported by "from rmidb2.model import *"
__all__ = ['Group', 'Permission', 'User', 'Visit', 'VisitIdentity']

from datetime import datetime

import re
import pkg_resources
pkg_resources.require('SQLObject>=0.10.1')

from turbogears.database import PackageHub
# import some basic SQLObject classes for declaring the data model
# (see http://www.sqlobject.org/SQLObject.html#declaring-the-class)
from sqlobject import SQLObject, SQLObjectNotFound, RelatedJoin
from sqlobject.inheritance import InheritableSQLObject
# import some datatypes for table columns from SQLObject
# (see http://www.sqlobject.org/SQLObject.html#column-types for more)
from sqlobject import StringCol, UnicodeCol, IntCol, DateTimeCol, FloatCol, ForeignKey, MultipleJoin
from sqlobject import DatabaseIndex
from sqlobject.dberrors import *
from turbogears import identity
import secpwhash 

__connection__ = hub = PackageHub('rmidb2')


# your data model
QUEUED = 'Queued'
RUNNING = 'Running'
ERROR = 'Error'
DONE = 'Done'
DELETED = 'Deleted'

# class YourDataClass(SQLObject):
class SearchList(SQLObject):
    title = UnicodeCol()
    query = UnicodeCol()
    max_mass = FloatCol()
    min_mass = FloatCol()
    mass_tolerance = FloatCol()
    spec_mode = UnicodeCol()
    database = UnicodeCol()
    created = DateTimeCol(default=datetime.now)
    status = UnicodeCol(default=QUEUED)
    user = ForeignKey('User',cascade=True)
    results = MultipleJoin("ResultList", joinColumn="search_id") # automatically add "_id" to "search" col in ResultList


class ResultList(SQLObject):
    microorganism_name = UnicodeCol()
    matching_hit = IntCol()
    p_value = FloatCol()
    e_value = FloatCol()
    search = ForeignKey("SearchList",cascade=True)
    matches = MultipleJoin("BiomarkerMatch",joinColumn='result_id')

class BiomarkerMatch(SQLObject):
    result = ForeignKey("ResultList",cascade=True)
    peak = FloatCol()
    bmmz = FloatCol()
    biomarker = ForeignKey("Biomarker",cascade=True)
    delta = FloatCol()
    index1 = DatabaseIndex('result')

class Biomarker(SQLObject):
    database = ForeignKey('Database',cascade=True)
    accession = StringCol(alternateID=True,length=128)
    gene = StringCol()
    organism = StringCol()
    description = StringCol()
    index1 = DatabaseIndex('database','accession',unique=True)

    @staticmethod
    def parse(description):
	accs,rest = description.split(None,1)
        acc = accs.split('|')[1]
	desc = rest.split(' OS=',1)[0]
	sd = re.split(r' ([A-Z][A-Z])=',rest)
        md = {}
	for i in range(1,len(sd),2):
	    key = sd[i]; value = sd[i+1]
	    md[key] = value
	return acc,md.get("GN",""),md.get("OS",""),desc
    @staticmethod
    def find(database,accession,description):
	acc,gene,org,desc = Biomarker.parse(description)
	try:
	    bm = Biomarker.selectBy(database=database,accession=acc)[0]
	except IndexError:
	    try:
	        bm = Biomarker(database=database,accession=acc,gene=gene,description=desc,organism=org)
	    except DuplicateEntryError:
		bm = Biomarker.selectBy(database=database,accession=acc)[0]
	return bm

class Database(SQLObject):
    name = StringCol(alternateID=True,length=1024)
    index1 = DatabaseIndex('name')
    
    @staticmethod
    def find(name):
	try:
	    db = Database.byName(name)
	except SQLObjectNotFound:
	    try:
	        db = Database(name=name)
	    except DuplicateEntryError:
		db = Database.byName(name)
	return db
	

# the identity model

class Visit(SQLObject):
    """A visit to your site."""

    visit_key = StringCol(length=40, alternateID=True,
                          alternateMethodName='by_visit_key')
    created = DateTimeCol(default=datetime.now)
    expiry = DateTimeCol()

    @classmethod
    def lookup_visit(cls, visit_key):
        try:
            return cls.by_visit_key(visit_key)
        except SQLObjectNotFound:
            return None


class VisitIdentity(SQLObject):
    """A Visit that is linked to a User object."""

    visit_key = StringCol(length=40, alternateID=True,
                          alternateMethodName='by_visit_key')
    user_id = IntCol()


class Group(SQLObject):
    """An ultra-simple Group definition."""

    # names like "user" and "group" are reserved words in SQL
    # so we set the name to something safe for SQL
    class sqlmeta:
        table = 'tg_group'

    def __repr__(self):
        return '<Group: name="%s", display_name="%s">' % (
            self.group_name, self.display_name)

    def __unicode__(self):
        return self.display_name or self.group_name

    group_name = UnicodeCol(length=16, alternateID=True,
                            alternateMethodName='by_group_name')
    display_name = UnicodeCol(length=255)
    created = DateTimeCol(default=datetime.now)

    # collection of all users belonging to this group
    users = RelatedJoin('User', intermediateTable='user_group',
                        joinColumn='group_id', otherColumn='user_id')

    # collection of all permissions for this group
    permissions = RelatedJoin('Permission', joinColumn='group_id',
                              intermediateTable='group_permission',
                              otherColumn='permission_id')


class User(SQLObject):

    # names like "user" and "group" are reserved words in SQL
    # so we set the name to something safe for SQL
    class sqlmeta:
        table = 'tg_user'

    user_name = UnicodeCol(length=16, alternateID=True,
                           alternateMethodName='by_user_name')
    email_address = UnicodeCol(length=255, alternateID=True,
                               alternateMethodName='by_email_address')
    display_name = UnicodeCol(length=255)
    password = StringCol(length=160)
    created = DateTimeCol(default=datetime.now)
    last_login = DateTimeCol(default=None)

    # groups this user belongs to
    groups = RelatedJoin('Group', intermediateTable='user_group',
                         joinColumn='user_id', otherColumn='group_id')
    # searches belong to this user
    searches = MultipleJoin("SearchList",joinColumn='user_id')

    def __repr__(self):
        return '<User: name="%s", display name="%s">' % (
            self.user_name, self.display_name)

    def __unicode__(self):
        return self.display_name or self.user_name

    def _get_permissions(self):
        perms = set()
        for g in self.groups:
            perms |= set(g.permissions)
        return perms

    def _set_password(self, cleartext_password):
        """Run cleartext_password through the hash algorithm before saving."""
        password_hash = secpwhash.hash_password(cleartext_password)
        self._SO_set_password(password_hash)

    def set_password_raw(self, password):
        """Saves the password as-is to the database."""
        self._SO_set_password(password)

    def is_guest(self):
	return identity.in_group('guest')

    def is_validated(self):
	return identity.in_group('validated')

    def is_admin(self):
	return identity.in_group('admin')

class Permission(SQLObject):
    """A relationship that determines what each Group can do."""

    permission_name = UnicodeCol(length=16, alternateID=True,
                                 alternateMethodName='by_permission_name')
    description = UnicodeCol(length=255)

    groups = RelatedJoin('Group',
                         intermediateTable='group_permission',
                         joinColumn='permission_id',
                         otherColumn='group_id')

    def __repr__(self):
        return '<Permission: name="%s">' % self.permission_name

    def __unicode__(self):
        return self.permission_name


# functions for populating the database

def bootstrap_model(clean=False, user=None):
    """Create all database tables and fill them with default data.

    This function is run by the 'bootstrap' function from the command module.
    By default it calls two functions to create all database tables for your
    model and optionally create a user.

    You can add more functions as you like to add more boostrap data to the
    database or enhance the functions below.

    If 'clean' is True, all tables defined by your model will be dropped before
    creating them again. If 'user' is not None, 'create_user' will be called
    with the given username.

    """
    create_tables(clean)
    if user:
        create_default_user(user)

def create_tables(drop_all=False):
    """Create all tables defined in the model in the database.

    Optionally drop existing tables before creating them.

    """
    from turbogears.util import get_model
    from inspect import isclass

    model = get_model()
    if not model:
        from rmidb2.command import ConfigurationError
        raise ConfigurationError(
            "Unable to create database tables without a model")

    try:
        so_classes = [model.__dict__[x] for x in model.soClasses]
    except AttributeError:
        so_classes = model.__dict__.values()

    if drop_all:
        print "Dropping all database tables defined in model."
        for item in reversed(so_classes):
            if (isclass(item) and issubclass(item, SQLObject)
                    and item is not SQLObject
                    and item is not InheritableSQLObject):
                item.dropTable(ifExists=True, cascade=True)

    # list of constraints we will collect
    constraints = list()

    for item in so_classes:
        if (isclass(item) and issubclass(item, SQLObject)
                and item is not SQLObject
                and item is not InheritableSQLObject):
            # create table without applying constraints, collect
            # all the constaints for later creation.
            # see http://sqlobject.org/FAQ.html#mutually-referencing-tables
            # for more info
            collected_constraints = item.createTable(
                ifNotExists=True, applyConstraints=False)

            if collected_constraints:
                constraints.extend(collected_constraints)

    # now that all tables are created, add the constaints we collected
    for postponed_constraint in constraints:
        # item is the last processed item and we borrow its connection
        item._connection.query(postponed_constraint)

    print "All database tables defined in model created."

def create_default_users():
    create_admin()
    create_guest()
    create_groups()
    create_guest_example()

def create_groups():
    hub.begin()
    try:
        g = Group(group_name='validated', display_name='Validated')
    except DuplicateEntryError:
        g = Group.by_group_name('validated')
    u = User.by_user_name('admin')
    if g not in u.groups:
	g.addUser(u)
    u = User.by_user_name('guest')
    if g not in u.groups:
	g.addUser(u)
    try:
        g = Group(group_name='unvalidated', display_name='Unvalidated')
    except DuplicateEntryError:
        pass
    hub.commit()

def create_admin():
    hub.begin()
    try:
        u = User(user_name='admin', display_name=u"Administrator",
	         email_address="admin@localhost",
                 password="testing123")
    except DuplicateEntryError:
	u = User.by_user_name('admin')
    try:
        g = Group(group_name='admin', display_name='Administrator')
    except DuplicateEntryError:
	g = Group.selectBy(group_name='admin')[0]
    if g not in u.groups:
        u.addGroup(g)
    hub.commit()

def create_guest():
    hub.begin()
    try:
        u = User(user_name='guest', display_name="Guest",
	         email_address="guest@localhost",
                 password="")
    except DuplicateEntryError:
	u = User.by_user_name('guest')
    try:
        g = Group(group_name='guest', display_name='Guest')
    except DuplicateEntryError:
	g = Group.selectBy(group_name='guest')[0]
    if g not in u.groups:
        u.addGroup(g)
    hub.commit()

def create_guest_example():
    if SearchList.select().count() == 0:
        s = SearchList(title="Example: B. subtilis, Positive mode (Pineda et al., 2003)", min_mass=4000.0, max_mass=15000.0, query="4272.29\t4306.49\t4344.59\t4420.69\t4604.99\t4734.79\t4943.49\t5002.39\t5225.09\t5253.99\t5291.19\t5571.79\t5900.39\t6506.69\t6596.59\t6637.49\t6676.99\t6697.19\t7112.89\t7424.59\t7712.79\t8834.89\t9468.79\t10444.19", mass_tolerance=3.0, spec_mode='Positive', database="Ribosomal Proteins in Bacteria: Reviewed", user=User.by_user_name('guest'))
        from async import MicroorganismIdentification
        MicroorganismIdentification()

def create_default_user(user_name, password=None):
    """Create a default user."""
    try:
        u = User.by_user_name(user_name)
    except:
        u = None
    if u:
        print "User '%s' already exists in database." % user_name
        return
    from getpass import getpass
    from sys import stdin
    while password is None:
        try:
            password = getpass("Enter password for user '%s': "
                % user_name.encode(stdin.encoding)).strip()
            password2 = getpass("Confirm password: ").strip()
            if password != password2:
                print "Passwords do not match."
            else:
                password = password.decode(stdin.encoding)
                break
        except (EOFError, KeyboardInterrupt):
            print "User creation cancelled."
            return
    hub.begin()
    u = User(user_name=user_name, display_name=u"Default User",
        email_address=u"%s@nowhere.xyz" % user_name, password=password)
    hub.commit()
    print "User '%s' created." % user_name

