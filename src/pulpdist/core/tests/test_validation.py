#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
"""Basic test suite for sync transfer operations"""

import shutil
import tempfile
import os.path
import json

from .compat import unittest
from .. import validation

TEST_SPEC = {
    "string": validation.check_text(),
    "number": validation.check_type(int),
    "sequence": validation.check_sequence(validation.check_type(int)),
}

class TestValidation(unittest.TestCase):

    def check_validator(self, validator, valid, invalid):
        for entry in valid:
            validator(entry)
        for entry in invalid:
            with self.assertRaises(validation.ValidationError) as exc:
                validator(entry)
            details = str(exc.exception)
            self.assertIn('setting', details)
            setting = 'example'
            with self.assertRaises(validation.ValidationError) as exc:
                validator(entry, setting)
            details = str(exc.exception)
            self.assertIn(setting, details)

    def test_check_values(self):
        allowed = range(5)
        self.check_validator(validation.check_value(allowed), allowed, [None, 10, ''])
        allowed = "one two three".split()
        self.check_validator(validation.check_value(allowed), allowed, [None, 10, ''])

    def test_check_type(self):
        self.check_validator(validation.check_type(str), [''], [None, 1])
        self.check_validator(validation.check_type(int), [1], [None, ''])

    def test_check_simple_id(self):
        valid = [u'hello', u'hello_world', u'hello-world']
        invalid = [None, 'hello world', 1]
        self.check_validator(validation.check_simple_id(), valid, invalid)

    def test_check_pulp_id(self):
        valid = [u'hello', u'hello_world']
        invalid = [None, 'hello-world', 'hello world', 1]
        self.check_validator(validation.check_pulp_id(), valid, invalid)

    def test_check_rsync_filter(self):
        valid = [u'hello', u'hello_world', u'hello-world', u'he??o*/w*rld.joy']
        invalid = [None, 'hello world', 1]
        self.check_validator(validation.check_rsync_filter(), valid, invalid)

    def test_check_host(self):
        valid = [u'hello', u'hello-world', u'hello.world', u'1.2.3.4']
        invalid = [None, 'hello_world', 'he??o*/w*rld.joy',
                   'hello/world', 'hello world', '1.2', 1]
        self.check_validator(validation.check_host(), valid, invalid)

    def test_check_path(self):
        valid = [u'hello', u'hello_world', u'hello-world', u'hello/world']
        invalid = [None, 'he??o*/w*rld.joy', 'hello world', 1]
        self.check_validator(validation.check_path(), valid, invalid)

    def test_check_remote_path(self):
        valid = [u'/hello/', u'/hello_world/', u'/hello-world/', u'/hello/world/']
        invalid = [None, 'hello', '/hello', 'hello/',
                   'he??o*/w*rld.joy', 'hello world', 1]
        self.check_validator(validation.check_remote_path(), valid, invalid)

    def test_check_sequence(self):
        validator = validation.check_sequence(validation.check_type(str))
        valid = [[], [''], ['', '']]
        invalid_subscripts = [[1, ''], ['', 1]]
        invalid = [None, 1, '', {}] + invalid_subscripts
        self.check_validator(validator, valid, invalid)
        for i, entry in enumerate(invalid_subscripts):
            with self.assertRaises(validation.ValidationError) as exc:
                validator(entry)
            details = str(exc.exception)
            self.assertIn('[{0}]'.format(i), details)

    def test_check_mapping(self):
        spec= TEST_SPEC
        validator = validation.check_mapping(spec)
        valid = [dict(string='', number=1, sequence=[1])]
        invalid_string = dict(string=1, number=1, sequence=[1])
        invalid_number = dict(string='', number='', sequence=[1])
        invalid_sequence = dict(string='', number='', sequence=[''])
        extra = dict(string='', number=1, sequence=[1], hello='world')
        missing = [{}, dict(string=''), dict(number=1), dict(sequence=[1])]
        invalid = [None, 1, '', invalid_string, invalid_number,
                   invalid_sequence, extra] + missing
        self.check_validator(validator, valid, invalid)
        invalid_subscripts = dict(string=invalid_string,
                                  number=invalid_number,
                                  sequence=invalid_sequence)
        for key, entry in invalid_subscripts.items():
            with self.assertRaises(validation.ValidationError) as exc:
                validator(entry)
            details = str(exc.exception)
            self.assertIn('[{0!r}]'.format(key), details)

    def test_valid_config(self):
        spec= TEST_SPEC
        valid = [dict(string='', number=1, sequence=[1])]
        for config in valid:
            validation.validate_config(config, spec)

    def test_invalid_config_wrong_type(self):
        spec= TEST_SPEC
        invalid = [1, '']
        for config in invalid:
            with self.assertRaises(validation.ValidationError) as exc:
                validation.validate_config(config, spec)
            details = str(exc.exception)
            self.assertIn('config', details)
            self.assertIn('mapping', details)
            self.assertIn(str(type(config)), details)

    def test_invalid_config_extra(self):
        spec= TEST_SPEC
        config = dict(string='', number=1, sequence=[1], hello='world')
        error = "['hello'] unexpected in config"
        with self.assertRaises(validation.ValidationError) as exc:
            validation.validate_config(config, spec)
        details = str(exc.exception)
        self.assertIn(error, details)
        self.assertIn(repr(config), details)

    def test_invalid_config_missing(self):
        spec= TEST_SPEC
        missing = [{}, dict(string=''), dict(number=1), dict(sequence=[1])]
        expected = set(spec)
        for config in missing:
            missing = sorted(expected - set(config))
            error = "{0!r} missing from config".format(missing)
            with self.assertRaises(validation.ValidationError) as exc:
                validation.validate_config(config, spec)
            details = str(exc.exception)
            self.assertIn(error, details)
            self.assertIn(repr(config), details)

    def test_invalid_config_entries(self):
        spec= TEST_SPEC
        invalid_string = dict(string=1, number=1, sequence=[1])
        invalid_number = dict(string='', number='', sequence=[1])
        invalid_sequence = dict(string='', number='', sequence=[''])
        invalid_subscripts = dict(string=invalid_string,
                                  number=invalid_number,
                                  sequence=invalid_sequence)
        for key, config in invalid_subscripts.items():
            with self.assertRaises(validation.ValidationError) as exc:
                validation.validate_config(config, spec)
            details = str(exc.exception)
            self.assertIn('config[{0!r}]'.format(key), details)

    def test_allow_none(self):
        validators = [
            validation.check_type(int, allow_none=True),
            validation.check_pulp_id(allow_none=True),
            validation.check_rsync_filter(allow_none=True),
            validation.check_host(allow_none=True),
            validation.check_path(allow_none=True),
            validation.check_remote_path(allow_none=True),
            validation.check_sequence(validation.check_type(str), allow_none=True),
            validation.check_mapping(TEST_SPEC, allow_none=True),
        ]
        for validator in validators:
            validator(None)


class ExampleConfig(validation.ValidatedConfig):
    _SPEC = TEST_SPEC

EXAMPLE_DATA = {
    "string": "",
    "number": 1,
    "sequence": [2],
}

class TestValidatedConfig(unittest.TestCase):
    # TODO: Make this more comprehensive

    def test_ensure_validated(self):
        data = EXAMPLE_DATA
        config = ExampleConfig.ensure_validated(data)
        self.assertEqual(config, data)
        self.assertIsNot(config, data)

    def test_from_json(self):
        data = EXAMPLE_DATA
        example = ExampleConfig.from_json(json.dumps(data))
        self.assertEqual(example.config, data)


if __name__ == '__main__':
    unittest.main()
