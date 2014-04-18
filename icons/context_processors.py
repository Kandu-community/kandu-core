from django.utils.functional import SimpleLazyObject

from models import Icon

def add_icons(request):
	return {
		'logo': Icon.objects.filter(partner_icon=False).first(),
		'partners_logos': Icon.objects.filter(partner_icon=True)
	}