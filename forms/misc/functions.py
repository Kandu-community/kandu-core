#coding:utf-8

from django.db.models import Model, ForeignKey, ImageField, DateTimeField
from django.contrib.auth.models import User, Group
from django.dispatch import receiver
from django.db.models import signals
from django.contrib.gis.db.models import PointField
from model_utils.managers import InheritanceManager
from django.contrib.gis.geos import Point
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.urlresolvers import reverse
import json
import re
import itertools
import os
import subprocess


def generate_name(verbose_name):
	no_spaces = re.sub(r'\s', r'_', verbose_name.strip())
	return re.sub(r'[^_\w\d]', r'', no_spaces)

def write_group(group_verbose_names):
	for group_name in group_verbose_names:
		group, created = Group.objects.get_or_create(name=group_name)
	
	return u"\tuser_group_names = %s\n" % group_verbose_names

def write_label_fields(fields, form_object):
	field_names = []
	for field_name in fields:
		try:
			next(field for field in form_object['fields'] if field['name'] == field_name)
		except StopIteration:
			raise ValueError('Field {field_name} is referenced in "fields_for_label" of {model_name} but not defined'.format(field_name=field_name, model_name=form_object['name']))
		except KeyError as error:
			raise ValueError('Field of form %r is missing %r param.' % (form_object['name'], error.args[0]))

		field_names.append(generate_name(field_name))

	return u"\tlabel_fields = %r\n" % field_names

def write_plain_fields(form_object):
	output = ''

	for field_name in ['show_on_map', 'is_editable', 'is_creatable']:
		try:
			output += u"\t{name} = {value}\n".format(value=form_object[field_name], name=field_name)
		except KeyError:
			continue

	return output

def write_visibility_dependencies(aggregate):
	if len(aggregate.keys()) == 0:
		return ''

	aggregate_processed = {
		generate_name(field_name) : {
			generate_name(other_field) : other_value
			for other_field, other_value in conditions.items()
		}
		for field_name, conditions in aggregate.items()
	}

	return u"\tvisibility_dependencies = %s\n" % aggregate_processed

def write_model(verbose_name, form_object):
	output = u"class {name}(BaseFormModel):\n\tclass Meta:\n\t\tverbose_name = u'{verbose_name}'\n\tobjects = GeoManager()\n".format(
		name=generate_name(verbose_name), 
		verbose_name=verbose_name
	)
	try:
		if form_object.get('is_creatable', True):
			output += u"\tcategory = u'{}'\n".format(form_object['category'])
		return output
	except KeyError:
		raise ValueError('%s form doesn\'t specify "category", which is mandatory' % verbose_name)

allowed_extra_args = ['help_text', 'max_length', 'to', 'choices']

def write_field(field_object, form_name):
	from fields import load_field
	try:
		return load_field(field_object).render_django()
	except ValueError as error:
		raise ValueError('Form %r: %s' % (form_name, str(error)))

def create_model(form_object, collected_output, counter):
	output = ''

	try:
		output += write_model(form_object['name'], form_object)
	except KeyError as error:
		raise ValueError('Form is missing %r param. This info might help you locate the form: %r' % (error.args[0], form_object))

	output += '\tdeclared_num = %d\n' % counter()
	output += write_group(form_object.get('user_groups', ['basic']))
	if form_object.has_key('fields_for_label'):
		output += write_label_fields(form_object['fields_for_label'], form_object)
	output += write_plain_fields(form_object)

	visible_when = {}
	for field_object in form_object['fields']:
		output += write_field(field_object, form_object['name'])
		
		if field_object.has_key('visible_when'):
			visible_when[field_object['name']] = field_object.get('visible_when')

	output += write_visibility_dependencies(visible_when)

	if form_object.has_key('inlines'):
		inlines_str = []
		for inline in form_object['inlines']:
			if isinstance(inline, basestring):
				inlines_str.append(generate_name(inline))
			elif isinstance(inline, dict):
				inline['is_creatable'] = False
				inlines_str.append(create_model(inline, collected_output, counter=counter))
			else:
				raise ValueError('"inlines" may contain only form names or json objects')

		output += '\tinlines = %r\n' % inlines_str
	
	collected_output.append(output)

	return generate_name(form_object['name'])

def config_to_models(config_file):
	'''
	Returns string with a declarations of Django models,
	generated from config_filename
	'''

	config_array = json.load(config_file)

	output = [u'''
#coding:utf-8
from django.db.models import *
from django.contrib.gis.db.models import PointField, GeoManager
from forms.misc import BaseFormModel
from multiselectfield import MultiSelectField
from django.contrib.gis.geos import Point
''']

	counter = itertools.count().next

	for form_object in config_array:
		model_and_dependent = []
		create_model(form_object, model_and_dependent, counter=counter)
		output += model_and_dependent

	return '\n'.join(output).encode('utf8')

def config_update_wrapper():
	# from utils import clear_app_cache
	
	models_filename = os.path.join(settings.BASE_DIR, 'forms', 'models.py')
	try:
		with open(models_filename, 'r') as models_file:
			models_old_str = models_file.read()
	except IOError: # nothing to backup
		models_old_str = ''

	try:
		with open(settings.CONFIG_FILE) as config_file:
			with open(models_filename, 'w') as models_file:
				models_file.write(config_to_models(config_file)) # overwriting models.py with freshly generated one

			# clear_app_cache('forms.models')
			try:
				os.remove(os.path.join(settings.BASE_DIR, 'forms', 'models.pyc'))
			except OSError:
				pass

			try:
				import forms.models
				reload(forms.models)
				call_command('validate')
				# subprocess.check_output(['python', os.path.join(settings.BASE_DIR, 'manage.py'), 'validate'], stderr=subprocess.STDOUT)
			except CommandError as error:
				raise ValueError(str(error))

	except ValueError as error: # something went wrong
		with open(models_filename, 'w') as models_file:
			models_file.write(models_old_str) # rolling back models.py to initial state
		try:
			os.remove(os.path.join(settings.BASE_DIR, 'forms', 'models.pyc'))
		except OSError:
			pass
		
		raise error