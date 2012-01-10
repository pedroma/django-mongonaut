#import re
#import sys

from django.contrib.sessions.backends.db import SessionStore
from django.conf import settings
from django import http
from django.views.decorators.csrf import csrf_protect
from django.contrib import sessions
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.utils.functional import update_wrapper
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache

from mongoengine.base import TopLevelDocumentMetaclass

from mongonaut.options import ModelAdmin

LOGIN_FORM_KEY = 'this_is_the_login_form'

try:
    SESSION = SessionStore(session_key='mongonaut')
except django.db.utils.DatabaseError:
    SESSION = {}

class NautSite(object):
    """
    A NautSite object encapsulates an instance of the mongonaut application, ready
    to be hooked in to your URLconf. Models are registered with the mongonaut using the
    register() method, and the get_urls() method can then be used to access Django view
    functions that present a full admin interface for the collection of registered
    models.
    """

    def __init__(self, name=None, app_name='admin'):
        try:
            SESSION['registry'] = {} # model_class class -> admin_class instance
        except django.db.utils.DatabaseError:
            SESSION = {}
            SESSION['registry'] = {}
        self.root_path = None
        if name is None:
            self.name = 'admin'
        else:
            self.name = name
        self.app_name = app_name

    def register(self, model_or_iterable, admin_class=None, **options):
        """
        Registers the given model(s) with the given mongonaut class.

        The model(s) should be Model classes, not instances.

        If an mongonaut class isn't given, it will use ModelAdmin (the default
        admin options). If keyword arguments are given -- e.g., list_display --
        they'll be applied as options to the admin class.

        If a model is already registered, this will raise AlreadyRegistered.

        If a model is abstract, this will raise ImproperlyConfigured.
        """
        
        if not admin_class:
            admin_class = ModelAdmin
            
        if isinstance(model_or_iterable, TopLevelDocumentMetaclass):
            model_or_iterable = [model_or_iterable]
            
        for model in model_or_iterable:            
            if model in self._registry:
                raise AlreadyRegistered('The model %s is already registered' % model.__name__)
                
                if options:
                    # For reasons I don't quite understand, without a __module__
                    # the created class appears to "live" in the wrong place,
                    # which causes issues later on.
                    options['__module__'] = __name__
                    admin_class = type("%sAdmin" % model.__name__, (admin_class,), options)                

        # Instantiate the admin class to save in the registry
        SESSION['registry'][model] = admin_class(model, self)

    def unregister(self, model_or_iterable):
        """
        Unregisters the given model(s).

        If a model isn't already registered, this will raise NotRegistered.
        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotRegistered('The model %s is not registered' % model.__name__)
            del SESSION['registry'][model]
            


# This global object represents the default admin site, for the common case.
# You can instantiate AdminSite in your own code to create a custom admin site.
site = NautSite()