# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'BaseFormModel'
        db.create_table(u'forms_baseformmodel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal(u'forms', ['BaseFormModel'])

        # Adding model 'TestForm'
        db.create_table(u'forms_testform', (
            (u'baseformmodel_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['forms.BaseFormModel'], unique=True, primary_key=True)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('age', self.gf('django.db.models.fields.IntegerField')(blank=True)),
        ))
        db.send_create_signal(u'forms', ['TestForm'])

        # Adding model 'SecondForm'
        db.create_table(u'forms_secondform', (
            (u'baseformmodel_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['forms.BaseFormModel'], unique=True, primary_key=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')()),
            ('related_to', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['forms.TestForm'])),
        ))
        db.send_create_signal(u'forms', ['SecondForm'])


    def backwards(self, orm):
        # Deleting model 'BaseFormModel'
        db.delete_table(u'forms_baseformmodel')

        # Deleting model 'TestForm'
        db.delete_table(u'forms_testform')

        # Deleting model 'SecondForm'
        db.delete_table(u'forms_secondform')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'forms.baseformmodel': {
            'Meta': {'object_name': 'BaseFormModel'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'forms.secondform': {
            'Meta': {'object_name': 'SecondForm', '_ormbases': [u'forms.BaseFormModel']},
            'active': ('django.db.models.fields.BooleanField', [], {}),
            u'baseformmodel_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['forms.BaseFormModel']", 'unique': 'True', 'primary_key': 'True'}),
            'related_to': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['forms.TestForm']"})
        },
        u'forms.testform': {
            'Meta': {'object_name': 'TestForm', '_ormbases': [u'forms.BaseFormModel']},
            'age': ('django.db.models.fields.IntegerField', [], {'blank': 'True'}),
            u'baseformmodel_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['forms.BaseFormModel']", 'unique': 'True', 'primary_key': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['forms']