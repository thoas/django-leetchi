# -*- coding: utf-8 -*-
import django

from django.utils import translation
from django.conf import settings
from django.core import exceptions
from django.utils.importlib import import_module

CLASS_PATH_ERROR = 'djleetchi is unable to interpret settings value for %s. '\
                   '%s should be in the form of a tupple: '\
                   '(\'path.to.models.Class\', \'app_label\').'


def get_current_lang():
    try:
        lang = translation.get_language()[:2]
        if lang not in [l[0] for l in settings.LANGUAGES]:
            raise
    except:
        lang = settings.LANGUAGE_CODE
    return lang


def load_class(class_path, setting_name=None):
    """
    Loads a class given a class_path. The setting value may be a string or a
    tuple.

    The setting_name parameter is only there for pretty error output, and
    therefore is optional
    """
    if not isinstance(class_path, basestring):
        try:
            class_path, app_label = class_path
        except:
            if setting_name:
                raise exceptions.ImproperlyConfigured(CLASS_PATH_ERROR % (
                    setting_name, setting_name))
            else:
                raise exceptions.ImproperlyConfigured(CLASS_PATH_ERROR % (
                    'this setting', 'It'))

    try:
        class_module, class_name = class_path.rsplit('.', 1)
    except ValueError:
        if setting_name:
            txt = '%s isn\'t a valid module. Check your %s setting' % (
                class_path, setting_name)
        else:
            txt = '%s isn\'t a valid module.' % class_path
        raise exceptions.ImproperlyConfigured(txt)

    try:
        mod = import_module(class_module)
    except ImportError, e:
        if setting_name:
            txt = 'Error importing backend %s: "%s". Check your %s setting' % (
                class_module, e, setting_name)
        else:
            txt = 'Error importing backend %s: "%s".' % (class_module, e)

        raise exceptions.ImproperlyConfigured(txt)

    try:
        clazz = getattr(mod, class_name)
    except AttributeError:
        if setting_name:
            txt = ('Backend module "%s" does not define a "%s" class. Check'
                   ' your %s setting' % (class_module, class_name,
                                         setting_name))
        else:
            txt = 'Backend module "%s" does not define a "%s" class.' % (
                class_module, class_name)
        raise exceptions.ImproperlyConfigured(txt)
    return clazz

if django.VERSION >= (1, 5):
    update_fields = lambda instance, fields: instance.save(update_fields=fields)
else:
    update_fields = lambda instance, fields: instance.save()
