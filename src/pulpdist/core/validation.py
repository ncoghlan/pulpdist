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
"""Config definitions and helpers for pulpdist importer plugins"""
import re

class ValidationError(Exception): pass

def _fail_validation(fmt, *args, **kwds):
    raise ValidationError(fmt.format(*args, **kwds))

def check_type(expected_type):
    def validator(value, setting='setting'):
        if not isinstance(value, expected_type):
            _fail_validation("Expected {!r} for {}, got {!r}",
                             expected_type, setting, type(value))
    return validator

def check_regex(pattern, expected):
    _validate_str = check_type(str)
    def validator(value, setting='setting'):
        _validate_str(value, setting)
        if re.match(pattern, value) is None:
            _fail_validation("Expected {} for {}, got {!r}",
                             expected, setting, value)
    return validator

PULP_ID_REGEX = r'^[_A-Za-z]+$'
def check_pulp_id():
    return check_regex(PULP_ID_REGEX, 'valid Pulp ID')

VALID_FILTER_REGEX = r'^[*?\w@%+=:,./-]*$'
def check_rsync_filter():
    return check_regex(VALID_FILTER_REGEX, 'valid rsync filter')

# We seriously need some better URL handling infrastructure in the stdlib...
# From http://stackoverflow.com/questions/106179/regular-expression-to-match-hostname-or-ip-address
IP_REGEX = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$";
HOSTNAME_REGEX = "^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$";
VALID_HOST_REGEX = "({})|({})".format(IP_REGEX, HOSTNAME_REGEX)

def check_host():
    return check_regex(VALID_HOST_REGEX, 'valid host')

VALID_PATH_REGEX = r'^[\w@%+=:,./-]*$'
def check_path():
    return check_regex(VALID_PATH_REGEX, 'valid filesystem path')

def check_remote_path():
    _validate_path = check_path()
    def validator(value, setting='setting'):
        _validate_path(value, setting)
        if not value.startswith('/') or not value.endswith('/'):
            _fail_validation("{!r} must start and end with '/' "
                             "characters, got {!r}",
                             setting, value)
    return validator

def check_list(item_validator):
    def validator(value, setting='setting'):
        if not isinstance(value, list):
            _fail_validation("Expected list for {!r}, got {!r}",
                              setting, type(value))
        for i, item in enumerate(value):
            item_setting = setting + "[{}]".format(i)
            item_validator(item, item_setting)
    return validator

def check_mapping(spec):
    def validator(value, setting='setting'):
        # Check we've been given a mapping
        try:
            value_items = value.items()
        except (AttributeError, TypeError):
            _fail_validation("Expected mapping for {}, got {!r}",
                                setting, type(value))
        # Check for missing and extra attributes
        provided = set(value)
        expected = set(spec)
        missing = expected - provided
        if missing:
            _fail_validation("{!r} missing from {}, got {!r}",
                            sorted(missing), setting, value)
        extra = provided - expected
        if extra:
            _fail_validation("{!r} unexpected in {}, got {!r}",
                            sorted(extra), setting, value)
        # Check the validation of the individual items
        for key, value in value_items:
            value_setting = setting + "[{!r}]".format(key)
            spec[key](value, value_setting)
    return validator

def validate_config(config, spec):
    check_mapping(spec)(config, 'config')




















