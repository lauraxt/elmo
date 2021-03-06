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
#   Peter Bengtsson <peterbe@mozilla.com>
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

import os
from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User

# lib.auth.backends expects the LDAP_* to be set up
# fake that so we can import MozLdapBackend
settings.LDAP_HOST = settings.LDAP_DN = settings.LDAP_PASSWORD = 'test'
from lib.auth.backends import MozLdapBackend

from mock import Mock
from nose.tools import eq_, ok_
import ldap

# REMEMBER TO add mock to requirements

class LDAPAuthTestCase(TestCase):

    def setUp(self):
        super(LDAPAuthTestCase, self).setUp()
        self.fake_user = [
          ('mail=pbengtsson@mozilla.com,...',
           {'cn': ['Peter Bengtsson'],
            'givenName': ['Pet\xc3\xa3r'], # utf-8 encoded
            'mail': ['peterbe@mozilla.com'],
            'sn': ['Bengtss\xc2\xa2n'],
            'uid': ['pbengtsson']
            })
        ]
        self.fake_group = [
          ('cn=scm_l10n,ou=groups,dc=mozilla',
           {'cn': ['something'],
            'gidNumber': ['000'],
            'memberUid': ['hg', 'cool@mozilla.com'],
            'objectClass': ['posixGroup', 'top']
            })
        ]

    def test_authenticate_without_ldap(self):
        assert not User.objects.all().exists()
        user = User.objects.create(username='foo', email='foo@mozilla.com')
        user.set_password('secret')
        user.save()

        backend = MozLdapBackend()
        eq_(backend.authenticate('foo@mozilla.com', 'secret'),
                         user)
        eq_(backend.authenticate('foo', 'secret'), user)
        eq_(backend.authenticate('foo', 'JUNK'), None)

    def test_backend_cert_file(self):
        backend = MozLdapBackend()
        ok_(backend.certfile)
        ok_(os.path.isfile(os.path.abspath(backend.certfile)))

    def test_authenticate_with_ldap_new_user(self):
        assert not User.objects.all().exists()
        ldap.open = Mock('ldap.open')
        ldap.open.mock_returns = Mock('ldap_connection')
        ldap.set_option = Mock(return_value=None)

        ldap.initialize = Mock(return_value=MockLDAP({
          'dc=mozilla': self.fake_user,
          'ou=groups,dc=mozilla': self.fake_group
        }))
        backend = MozLdapBackend()

        user = backend.authenticate('foo', 'secret')
        ok_(user)
        ok_(User.objects.get(username='foo'))
        user = User.objects.get(first_name=u'Pet\xe3r')
        eq_(user.last_name, u'Bengtss\xa2n')
        ok_(not user.has_usable_password())
        ok_(not user.check_password('secret'))

    def test_authenticate_with_ldap_new_user_with_long_email(self):
        assert not User.objects.all().exists()
        ldap.open = Mock('ldap.open')
        ldap.open.mock_returns = Mock('ldap_connection')
        ldap.set_option = Mock(return_value=None)

        long_email = 'peter.anders.bengt.bengtsson@mozilla-europe.org.com'
        fake_user = [
          ('mail=%s,...' % long_email,
           {'cn': ['Peter Bengtsson'],
            'givenName': ['Pet\xc3\xa3r'], # utf-8 encoded
            'mail': [long_email],
            'sn': ['Bengtss\xc2\xa2n'],
            'uid': ['pbengtsson']
            })
        ]

        ldap.initialize = Mock(return_value=MockLDAP({
          'dc=mozilla': fake_user,
          'ou=groups,dc=mozilla': self.fake_group
        }))
        backend = MozLdapBackend()

        user = backend.authenticate(long_email, 'secret')
        ok_(user)
        ok_(User.objects.get(email=long_email))
        ok_(len(User.objects.get(email=long_email).username) <= 30)
        user = User.objects.get(first_name=u'Pet\xe3r')
        eq_(user.last_name, u'Bengtss\xa2n')
        ok_(not user.has_usable_password())
        ok_(not user.check_password('secret'))


    def test_authenticate_with_ldap_existing_user(self):
        assert not User.objects.all().exists()
        user = User.objects.create(
          username='foo',
          first_name=u'P\xe4ter',
          last_name=u'B\xa3ngtsson',
        )
        user.set_unusable_password()
        user.save()

        ldap.open = Mock('ldap.open')
        ldap.open.mock_returns = Mock('ldap_connection')
        ldap.set_option = Mock(return_value=None)

        ldap.initialize = Mock(return_value=MockLDAP({
          'dc=mozilla': self.fake_user,
          'ou=groups,dc=mozilla': self.fake_group
        }))
        backend = MozLdapBackend()

        user = backend.authenticate('foo', 'secret')
        ok_(user)
        _first_name = self.fake_user[0][1]['givenName'][0]
        eq_(user.first_name, unicode(_first_name, 'utf-8'))
        _last_name = self.fake_user[0][1]['sn'][0]
        eq_(user.last_name, unicode(_last_name, 'utf-8'))
        eq_(user.email, self.fake_user[0][1]['mail'][0])

        user_saved = User.objects.get(username='foo')
        eq_(user_saved.first_name, user.first_name)
        eq_(user_saved.last_name, user.last_name)

    def test_authenticate_with_ldap_wrong_password(self):
        ldap.initialize = Mock(return_value=MockLDAP({
          'dc=mozilla': self.fake_user,
          'ou=groups,dc=mozilla': self.fake_group
        }, credentials={
          self.fake_user[0][0]: 'rightsecret'
        }))
        backend = MozLdapBackend()
        user = backend.authenticate('foo', 'secret')
        eq_(user, None)

    def test_authenticate_with_ldap_wrong_username(self):
        ldap.initialize = Mock(return_value=MockLDAP({
          'dc=mozilla': self.fake_user,
          'ou=groups,dc=mozilla': self.fake_group
        }, credentials={
          'some-other-uid': 'secret'
        }))
        backend = MozLdapBackend()
        user = backend.authenticate('foo', 'secret')
        eq_(user, None)

    def test_authentication_ldap_username_not_recognized(self):
        ldap.initialize = Mock(return_value=MockLDAP({
          'dc=mozilla': None,
          'ou=groups,dc=mozilla': self.fake_group
        }, credentials={
          self.fake_user[0][0]: 'secret'
        }))
        backend = MozLdapBackend()
        user = backend.authenticate('foo', 'secret')
        ok_(not user)



class MockLDAP:
    def __init__(self, search_result, credentials=None):
        self.search_result = search_result
        self.credentials = credentials

    def search_s(self, search, *args, **kargs):
        return self.search_result[search]

    def simple_bind_s(self, dn, password):
        if self.credentials is None:
            # password check passed
            return
        if dn == settings.LDAP_DN:
            # sure, pretend we can connect successfully
            return
        try:
            if self.credentials[dn] != password:
                raise ldap.INVALID_CREDENTIALS
        except KeyError:
            raise ldap.UNWILLING_TO_PERFORM

    def void(self, *args, **kwargs):
        pass

    set_option = unbind_s = void
