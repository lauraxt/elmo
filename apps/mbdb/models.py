# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

'''Models representing statuses of buildbot builds on multiple masters.
'''

import pickle

from django.db import models
import fields
from django.conf import settings

class Master(models.Model):
    """Model for a buildbot master"""
    name = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return self.name

class Slave(models.Model):
    """Model for a build slave"""
    name = models.CharField(max_length=150, unique=True)

    def __unicode__(self):
        return self.name

class File(models.Model):
    """Model for files throughout"""
    # not  unique = True, mysql doesn't like long unique utf-8 strings
    path = models.CharField(max_length=400, db_index=True)

    def __unicode__(self):
        return self.path


class Tag(models.Model):
    """Model to add tags to the Change model"""
    value = models.CharField(max_length = 50, db_index = True, unique = True)

    def __unicode__(self):
        return self.value


class Change(models.Model):
    """Model for buildbot.changes.changes.Change"""
    number = models.PositiveIntegerField()
    master = models.ForeignKey(Master)
    branch = models.CharField(max_length = 100, null = True, blank = True)
    revision = models.CharField(max_length = 50, null = True, blank = True)
    who = models.CharField(max_length = 100, null = True, blank = True,
                           db_index = True)
    files = models.ManyToManyField(File)
    comments = models.TextField(null = True, blank = True)
    when = models.DateTimeField()
    tags = models.ManyToManyField(Tag)

    class Meta:
        unique_together = (('number', 'master'),)

    def __unicode__(self):
        rv = u'Change %d' % self.number
        if self.branch:
            rv += ', ' + self.branch
        if self.tags:
            rv += u' (%s)' % ', '.join(map(unicode, self.tags.all()))
        return rv

class Change_Tags(models.Model):
    """Helper model for change.tags queries.

    This model maps the ManyToManyField between Tag and Change,
    and does not create any database entries itself, thanks to
    Meta.managed = False.
    """
    change = models.ForeignKey(Change)
    tag = models.ForeignKey(Tag)
    class Meta:
        unique_together = (('change','tag'),)
        managed = False


class SourceStamp(models.Model):
    changes = models.ManyToManyField(Change, through='NumberedChange',
                                     related_name='stamps')
    branch = models.CharField(max_length = 100, null = True, blank = True)
    revision = models.CharField(max_length = 50, null = True, blank = True)

class NumberedChange(models.Model):
    change = models.ForeignKey(Change, related_name='numbered_changes')
    sourcestamp = models.ForeignKey(SourceStamp,
                                    related_name='numbered_changes')
    number = models.IntegerField(db_index = True)


class Property(models.Model):
    """Helper model for build properties.

    To support complex property values, they are internally pickled.
    """
    name            = models.CharField(max_length = 20, db_index = True)
    source          = models.CharField(max_length = 20, db_index = True)
    value           = fields.PickledObjectField(null = True, blank = True,
    # `db_index` commented out because the PickledObjectField is a BLOB/TEXT
    # field and will cause this error if you try to create it with Mysql
    # (1170, "BLOB/TEXT column 'value' used in key specification without a key length")
    # See http://stackoverflow.com/questions/1827063/mysql-error-key-specification-without-a-key-length/1827099#1827099
                                                #db_index = True,
                                                )
    class Meta:
        if settings.DATABASE_ENGINE != 'mysql':
            # hack around mysql, that doesn't do unique of unconstrained texts

            # peterbe: Commented out because I couldn't syncdb Mysql with this
            # see comment above about db_index=True on the value field
            pass#unique_together = (('name', 'source', 'value'),)


    def __unicode__(self):
        return "%s: %s" % (self.name, self.value)


class Builder(models.Model):
    """Model for buildbot.status.builder.BuilderStatus"""
    name     = models.CharField(max_length = 50, unique = True, db_index = True)
    master   = models.ForeignKey(Master, related_name='builders')
    category = models.CharField(max_length = 30, null = True, blank = True,
                                db_index = True)
    bigState = models.CharField(max_length = 30, null = True, blank = True)

    def __unicode__(self):
        return u'Builder <%s>' % self.name

class Build(models.Model):
    """Model for buildbot..status.builder.Build
    """
    buildnumber = models.IntegerField(null = True, db_index = True)
    properties  = models.ManyToManyField(Property, related_name = 'builds')
    builder     = models.ForeignKey(Builder, related_name = 'builds')
    slave       = models.ForeignKey(Slave, null=True, blank = True)
    starttime   = models.DateTimeField(null = True, blank = True)
    endtime     = models.DateTimeField(null = True, blank = True)
    result      = models.SmallIntegerField(null = True, blank = True)
    reason      = models.CharField(max_length = 50, null = True, blank = True)
    sourcestamp = models.ForeignKey(SourceStamp, null = True,
                                    related_name = 'builds')

    def setProperty(self, name, value, source):
        if name in ('buildername', 'buildnumber'):
            # we have those in the db, ignore
            return
        try:
            # First, see if we have the property, or a property of that name,
            # at least.
            prop = self.properties.get(name = name)
            if prop.value == value and prop.source == source:
                # we already know this, we're done
                return
            if prop.builds.count() < 2:
                # this is our own property, clean up the table
                prop.delete()
            else:
                # otherwise, unbind the property, and fake a DoesNotExist
                self.properties.remove(prop)
            raise Property.DoesNotExist(name)
        except Property.DoesNotExist:
            prop, created = Property.objects.get_or_create(name = name,
                                                           source = source,
                                                           value = value)
        self.properties.add(prop)
        self.save()

    def getProperty(self, name, default = None):
        if name == 'buildername':
            # hardcode, we know that
            return self.builder.name
        if name == 'buildnumber':
            # hardcode, we know that
            return self.buildnumber
        # all others are real properties, query the db
        try:
            prop = self.properties.get(name = name)
        except Property.DoesNotExist:
            return default
        return prop.value

    def propertiesAsList(self):
        l = [(p.name, p.value, p.source) for p in self.properties.iterator()]
        # hardcode buildername and buildnumber again
        l += [('buildername', self.builder.name, 'Build'),
              ('buildnumber', self.buildnumber, 'Build')]
        l.sort()
        return l

    def __unicode__(self):
        v = self.builder.name
        if self.buildnumber is not None:
            v += ': %d' % self.buildnumber
        return v


class Step(models.Model):
    name      = models.CharField(max_length=50)
    text      = fields.ListField(null = True, blank = True)
    text2     = fields.ListField(null = True, blank = True)
    result    = models.SmallIntegerField(null = True, blank = True)
    starttime = models.DateTimeField(null = True, blank = True)
    endtime   = models.DateTimeField(null = True, blank = True)
    build     = models.ForeignKey(Build, related_name = 'steps')


class URL(models.Model):
    name = models.CharField(max_length = 20)
    url = models.URLField()
    step = models.ForeignKey(Step, related_name = 'urls')


class Log(models.Model):
    name = models.CharField(max_length = 100, null = True, blank = True)
    filename = models.CharField(max_length = 200, unique = True,
                                null = True, blank = True)
    step = models.ForeignKey(Step, related_name = 'logs')
    isFinished = models.BooleanField(default = False)
    html = models.TextField(null = True, blank = True)

    def __unicode__(self):
        if self.filename:
            return self.filename
        return 'HTMLLog %d' % self.id


class BuildRequest(models.Model):
    """Buildrequest status model"""
    builder = models.ForeignKey(Builder)
    submitTime = models.DateTimeField()
    builds = models.ManyToManyField(Build, related_name='requests')
    sourcestamp = models.ForeignKey(SourceStamp, related_name='requests')