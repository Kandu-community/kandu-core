from django import forms
import autocomplete_light

from forms.utils import get_search_fields, get_form_models

class SearchAutocomplete(autocomplete_light.AutocompleteGenericBase):
	choices = []
	search_fields = []

	def choices_for_request(self):
		search_fields, choices = zip(*(
			(get_search_fields(form_class), form_class.objects.all()) for form_name, form_class 
			in get_form_models(for_user=self.request.user)
		))

		self.choices = choices
		self.search_fields = search_fields

		return super(SearchAutocomplete, self).choices_for_request()

autocomplete_light.register(SearchAutocomplete)

class SearchForm(forms.Form):
	query = forms.CharField(widget=autocomplete_light.TextWidget('SearchAutocomplete'))