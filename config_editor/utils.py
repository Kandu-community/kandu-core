import pickle
import json
import settings
from django import conf

from forms import misc


def get_root():
	try:
		with open(settings.EDITOR_PICKLE_FILE) as root_dump:
			root = pickle.load(root_dump)
		return root
	except IOError:
		with open(conf.settings.CONFIG_FILE) as config_file:
			root = misc.load_root(json.load(config_file))
		with open(settings.EDITOR_PICKLE_FILE, 'w') as root_dump:
			pickle.dump(root, root_dump)
		return root

def save_root(root):
	with open(settings.EDITOR_PICKLE_FILE, 'w') as root_dump:
		pickle.dump(root, root_dump)

def save_to_config(root):
	with open(conf.settings.CONFIG_FILE, 'w') as config_file:
		json.dump(root.render_json(), config_file, indent=2)

def reset_changes():
	with open(conf.settings.CONFIG_FILE) as config_file:
		root = misc.load_root(json.load(config_file))
	with open(settings.EDITOR_PICKLE_FILE, 'w') as root_dump:
		pickle.dump(root, root_dump)
	return root