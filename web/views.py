#coding:utf-8

from django.core.urlresolvers import reverse
from django.views.generic import ListView, CreateView, DeleteView, FormView, DetailView
from django.contrib.auth.forms import UserCreationForm
from django.forms.models import modelform_factory
from django.forms import Form, FileField, Field, Form
from django.contrib.auth.models import Group
from django.db.models import ForeignKey
from django.core.management import call_command
from django.http import HttpResponseRedirect, HttpResponseForbidden, HttpResponseNotFound, HttpResponseRedirect, HttpResponse
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
import os
from gmapi import maps
from gmapi.forms.widgets import GoogleMap
import autocomplete_light
from django.db import models
from django.contrib.gis.geoip import GeoIP, GeoIPException
from django.contrib.gis.db.models import PointField
from django.contrib.gis.measure import Distance
from django.contrib.gis.geos import Point
from extra_views import InlineFormSet, CreateWithInlinesView, UpdateWithInlinesView
from itertools import chain
from zipfile import ZipFile
from io import BytesIO

import forms.models
from forms.utils import get_form_models, get_search_fields
from forms.misc import BaseFormModel
from widgets import SearchForm, DatepickerWidget

class ModelFromUrlMixin(object):
	'''
	Makes CreateView, ListView, etc. get model name from
	url argument insted of "model" class attribute
	'''

	model_url_kwarg = 'model_name'
	inlines_also = False
	fail_silently_if_no_model_kwarg = False

	def parent_field_for_inline(self, inline_model):
		try:
			return next( 
				field.name for field in inline_model._meta.fields 
				if isinstance(field, ForeignKey) and field.rel.to == self.model and 
				field.name != 'baseformmodel_ptr_id' 
			)
		except StopIteration:
			raise ValueError('Inline form "%s" doesn\'t have a foreign key to it\'s parent "%s"' % (inline_model.verbose_name(), self.model.verbose_name()))

	def dispatch(self, *args, **kwargs):
		try:
			self.model = getattr(forms.models, self.kwargs[self.model_url_kwarg])
		except (AttributeError, KeyError):
			if self.fail_silently_if_no_model_kwarg:
				return super(ModelFromUrlMixin, self).dispatch(*args, **kwargs)
			else:
				return HttpResponseNotFound("No such form: %s" % self.kwargs[self.model_url_kwarg])

		if self.inlines_also and self.model.inlines:
			self.inlines = []
			for inline_model_name in self.model.inlines:
				inline_model = getattr(forms.models, inline_model_name)

				class FormModelInline(InlineFormSet):
					model = inline_model
					fk_name = self.parent_field_for_inline(inline_model)
					exclude = ('user',)
					extra = 1 # since we got dynamic "add another"

					def formfield_callback(self, model_field):
						from django.db.models import DateField

						if isinstance(model_field, DateField):
							return model_field.formfield(widget=DatepickerWidget)
						else:
							return model_field.formfield()

				self.inlines.append(FormModelInline)

		return super(ModelFromUrlMixin, self).dispatch(*args, **kwargs)

class InlineDefaultValueMixin(object):
	def forms_valid(self, form, inlines):
		if not form.instance.user_id:
			form.instance.user = self.request.user
		self.object = form.save()

		for formset in inlines:
			for instance in formset.save(commit=False):
				if not instance.user_id:
					instance.user = self.request.user
				instance.save()
					
		return HttpResponseRedirect(self.get_success_url())

class ExcludeFieldsMixin(object):
	'''
	Generates form from models, exculuding the fields
	needed to be excluded (eg. 'user', coordinates fields)
	'''

	def get_exclude_fields(self):
		exclude_fields = ['user', 'created_at']
		return exclude_fields

class HiddenFieldsMixin(object):
	def get_hidden_fields(self):
		hidden_fields = []
		if self.model.location_field():
			hidden_fields.append(self.model.location_field())

		return hidden_fields

class SuccessRedirectMixin(object):
	def get_success_url(self):
		return reverse('web_list')

class CheckPermissionsMixin(object):
	def dispatch(self, *args, **kwargs):
		if self.has_permission():
			return super(CheckPermissionsMixin, self).dispatch(*args, **kwargs)
		else:
			return HttpResponseForbidden("You don't have permission to perform this action.")

	def has_permission(self):
		if self.model:
			return self.model in [model for name, model in get_form_models(for_user=self.request.user)]
		else:
			return True

class MapMixin(object):
	def get_context_data(self, **kwargs):
		'''
		Adds a list of forms current user can fill into template context.
		'''
		context = super(MapMixin, self).get_context_data(**kwargs)

		context['map'] = self.get_map()
		return context

	def get_map(self):
		gmap = maps.Map()

		for form_object in self.object_list:
			if form_object.show_on_map:
				try:
					lng, lat = getattr(form_object, form_object.location_field()).coords
					marker = maps.Marker(opts = {
						'map': gmap,
						'position': maps.LatLng(lat, lng),
					})

					maps.event.addListener(marker, 'mouseover', 'myobj.markerOver')
					maps.event.addListener(marker, 'mouseout', 'myobj.markerOut')
					info = maps.InfoWindow({
						'content': '<a href="{url}">{text}</a>'.format(
							text = form_object.__unicode__().encode('utf-8'),
							url = reverse('web_update', kwargs={'model_name': form_object.model_name(), 'pk': form_object.pk})
						),
						'disableAutoPan': True
					})
					info.open(gmap, marker)
				except (TypeError, AttributeError): #no coordinates field or it has invalid value
					continue

		class MapForm(Form):
			map = Field(widget=GoogleMap(attrs={'width':800, 'height':550}))

		return MapForm(initial={'map': gmap})

class AutocompleteFormMixin(object):
	def get_form_class(self):
		if self.form_class:
			return self.form_class
		else:
			foreignkey_fields = [ 
				field.name for field in self.model._meta.fields 
				if isinstance(field, models.ForeignKey) or isinstance(field, models.ManyToManyField)
			]
			manytomany_fields = [ field.name for field in self.model._meta.many_to_many ]

			class AutocompleteForm(autocomplete_light.ModelForm):
				class Meta:
					model = self.model
					exclude = self.get_exclude_fields()
					autocomplete_fields = foreignkey_fields + manytomany_fields

				def __init__(form_self, *agrs, **kwargs):
					super(AutocompleteForm, form_self).__init__(*agrs, **kwargs)
					from django.forms import HiddenInput, DateField

					for field_name in form_self.fields:
						if field_name in self.get_hidden_fields():
							form_self.fields[field_name].widget = HiddenInput()
						if isinstance(form_self.fields[field_name], DateField):
							form_self.fields[field_name].widget = DatepickerWidget()

			return AutocompleteForm

class StaffOmnividenceMixin(object):
	def get_queryset(self):
		parent_queryset = super(StaffOmnividenceMixin, self).get_queryset()

		if self.request.user.is_staff:
			return parent_queryset
		else:
			return parent_queryset.filter(user=self.request.user)

def get_all_forms():
	return BaseFormModel.objects.order_by('-created_at').select_subclasses()

class BaseFormList(StaffOmnividenceMixin, ListView):
	template_name = 'web/form_list.html'
	paginate_by = 10
	
	def get_queryset(self):
		return get_all_forms()

class MapView(MapMixin, ListView):
	template_name = 'web/map_view.html'
	max_objects = 500

	def get_queryset(self):
		ip_address = self.request.META.get('REMOTE_ADDR', None)

		try:
			gi = GeoIP(settings.STATIC_ROOT)
			location = gi.lon_lat(ip_address)
		except GeoIPException:
			location = None

		object_list = []
		for form_name, form_model in get_form_models(for_user=self.request.user):
			try: # first closest objects
				object_list += list( form_model.objects.distance(Point(location), field_name=form_model.location_field()).order_by('distance')[:self.max_objects] )
			except (TypeError, AttributeError): # falling back to just first objects
				object_list += list(form_model.objects.order_by('created_at')[:self.max_objects])

		return object_list

class FormList(ModelFromUrlMixin, CheckPermissionsMixin, StaffOmnividenceMixin, ListView):
	template_name = 'web/form_list.html'
	paginate_by = 10

	def get_queryset(self):
		queryset = super(FormList, self).get_queryset()
		return queryset.order_by('-created_at')

	def get_context_data(self, **kwargs):
		context = super(FormList, self).get_context_data(**kwargs)
		context['object_list_model'] = self.object_list.model
		return context

class FormCreate(AutocompleteFormMixin, HiddenFieldsMixin, ExcludeFieldsMixin, SuccessRedirectMixin, InlineDefaultValueMixin, ModelFromUrlMixin, CheckPermissionsMixin, CreateWithInlinesView):
	template_name = 'web/form_create.html'
	inlines_also = True

class FormUpdate(AutocompleteFormMixin, HiddenFieldsMixin, ExcludeFieldsMixin, SuccessRedirectMixin, InlineDefaultValueMixin, ModelFromUrlMixin, CheckPermissionsMixin, UpdateWithInlinesView):
	template_name = 'web/form_update.html'
	inlines_also = True

	def has_permission(self):
		if not self.model.is_editable:
			return False
		else:
			return super(FormUpdate, self).has_permission()

class FormDelete(SuccessRedirectMixin, ModelFromUrlMixin, CheckPermissionsMixin, DeleteView):
	template_name = 'web/form_delete.html'

class DownloadFormFilesView(FormList):
	fail_silently_if_no_model_kwarg = True

	def get_queryset(self):
		try:
			return super(DownloadFormFilesView, self).get_queryset()
		except ImproperlyConfigured: # no model_name kwarg
			return get_all_forms()

	def get(self, request, *args, **kwargs):
		in_memory = BytesIO()
		with ZipFile(in_memory, "a") as zip_file:
			for form_object in self.get_queryset():
				if not form_object.allows_bulk_download:
					continue

				for field_name, attached_file in form_object.attached_files:
					try:
						zip_file.writestr(
							' '.join((form_object.model_name(), form_object.id_field_value or form_object.label_fields_as_str(), field_name)),
							attached_file.read()
						)
					except ValueError: # this field is empty, no problem
						continue

		response = HttpResponse(mimetype="application/zip")
		response["Content-Disposition"] = "attachment; filename=%s_images.zip" % (self.model.__name__ if self.model else 'all')

		in_memory.seek(0)    
		response.write(in_memory.read())
		return response


class UserRegistration(SuccessRedirectMixin, CreateView):
	template_name = 'web/user_registration.html'
	form_class = UserCreationForm

def search_redirect(request):
	garbage, pk = request.GET['identification'].split('-')
	return HttpResponseRedirect(BaseFormModel.objects.select_subclasses().get(pk=pk).get_absolute_url())

class ManageConfig(FormView):
	template_name = 'web/config_form.html'

	def get(self, request, *args, **kwargs):
		if kwargs.has_key('operation'):
			return getattr(self, kwargs['operation'])()
		else:
			return super(ManageConfig, self).get(request, *args, **kwargs)

	def get_form_class(self):
		class UploadConfigForm(Form):
			config_file = FileField()

		return UploadConfigForm

	def form_valid(self, form):
		from forms.misc import config_update_wrapper

		with open(settings.CONFIG_FILE, 'w') as config_file:
			config_file.write(form.cleaned_data['config_file'].read())

		try:
			config_update_wrapper()

			self.restart_server()
			messages.success(self.request, "Config updated successfully")
		except ValueError as error:
			messages.error(self.request, error)
		return HttpResponseRedirect(reverse('web_config'))

	def execute_script(self):
		from subprocess import call
		ret_code = call(os.path.join(settings.BASE_DIR, 'apply_config.sh'), shell=True)
		if ret_code == 0:
			return HttpResponseRedirect('/admin/')
		else:
			return HttpResponse('Script returned %d (something\'s not right)' % ret_code)

	def make_migration(self):
		# self.restart_server()

		try:
			call_command('schemamigration', 'forms', auto=True)
		except SystemExit:
			pass
		messages.success(self.request, "Migration made successfully")
		return HttpResponseRedirect(reverse('web_config'))

	def migrate(self):
		self.restart_server()

		call_command('migrate', noinput=True)

		messages.success(self.request, "Migration applied successfully")
		return HttpResponseRedirect(reverse('web_config'))