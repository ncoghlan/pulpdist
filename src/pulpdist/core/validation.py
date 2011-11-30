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

def check_type(expected_type, allow_none=False):
    def validator(value, setting='setting'):
        if allow_none and value is None:
            return
        if not isinstance(value, expected_type):
            _fail_validation("Expected {0!r} for {1}, got {2!r}",
                             expected_type, setting, type(value))
    return validator

def check_text(allow_none=False):
    # Allow either string type for now
    # TODO: Tighten this up to enforce unicode
    #       Means fixing deserialisation interfaces :P
    return check_type(basestring, allow_none)

def check_regex(pattern, expected, allow_none=False):
    _validate_text = check_text()
    def validator(value, setting='setting'):
        if allow_none and value is None:
            return
        _validate_text(value, setting)
        # We use Unicode storage, but stick with the ASCII rules
        # for pattern matching on whitespace etc.
        if re.match(pattern, value) is None:
            _fail_validation("Expected {0} for {1}, got {2!r}",
                             expected, setting, value)
    return validator

PULP_ID_REGEX = r'^[_A-Za-z]+$'
def check_pulp_id(allow_none=False):
    return check_regex(PULP_ID_REGEX, 'valid Pulp ID', allow_none)

VALID_FILTER_REGEX = r'^[*?\w@%+=:,./-]*$'
def check_rsync_filter(allow_none=False):
    return check_regex(VALID_FILTER_REGEX, 'valid rsync filter', allow_none)

# We seriously need some better URL handling infrastructure in the stdlib...
# From http://stackoverflow.com/questions/106179/regular-expression-to-match-hostname-or-ip-address
IPv4_REGEX = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$";
# TODO: Allow IPv6 addresses as well (for now: just use hostnames if you need to access an IPv6-only host)
HOSTNAME_REGEX = "^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$";
VALID_HOST_REGEX = "({0})|({1})".format(IPv4_REGEX, HOSTNAME_REGEX)

def check_host(allow_none=False):
    return check_regex(VALID_HOST_REGEX, 'valid host', allow_none)

VALID_PATH_REGEX = r'^[\w@%+=:,./-]*$'
def check_path(allow_none=False):
    return check_regex(VALID_PATH_REGEX, 'valid filesystem path', allow_none)

def check_remote_path(allow_none=False):
    _validate_path = check_path()
    def validator(value, setting='setting'):
        if allow_none and value is None:
            return
        _validate_path(value, setting)
        if not value.startswith('/') or not value.endswith('/'):
            _fail_validation("{0!r} must start and end with '/' "
                             "characters, got {1!r}",
                             setting, value)
    return validator

def check_sequence(item_validator, allow_none=False):
    def validator(value, setting='setting'):
        if allow_none and value is None:
            return
        # Check we've been given a sequence
        if isinstance(value, basestring):
            _fail_validation("Strings not accepted for {0!r}, got {1!r}",
                              setting, value)
        if hasattr(value, 'keys'):
            _fail_validation("Mappings not accepted for {0!r}, got {1!r}",
                              setting, type(value))
        try:
            itr = iter(value)
        except (TypeError, AttributeError):
            _fail_validation("Expected sequence for {0!r}, got {1!r}",
                              setting, type(value))
        # Check individual items
        for i, item in enumerate(itr):
            item_setting = setting + "[{0}]".format(i)
            item_validator(item, item_setting)
    return validator

def check_mapping(spec, allow_none=False):
    def validator(value, setting='setting'):
        if allow_none and value is None:
            return
        # Check we've been given a mapping
        try:
            value_items = value.items()
        except (AttributeError, TypeError):
            _fail_validation("Expected mapping for {0}, got {1!r}",
                                setting, type(value))
        # Check for missing and extra attributes
        provided = set(value)
        expected = set(spec)
        missing = expected - provided
        if missing:
            _fail_validation("{0!r} missing from {1}, got {2!r}",
                            sorted(missing), setting, value)
        extra = provided - expected
        if extra:
            _fail_validation("{0!r} unexpected in {1}, got {2!r}",
                            sorted(extra), setting, value)
        # Check the validation of the individual items
        for key, value in value_items:
            value_setting = setting + "[{0!r}]".format(key)
            spec[key](value, value_setting)
    return validator

def validate_config(config, spec):
    check_mapping(spec)(config, 'config')




















