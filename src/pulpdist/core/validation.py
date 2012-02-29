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
import copy

class ValidationError(Exception): pass

def fail_validation(fmt, *args, **kwds):
    raise ValidationError(str(fmt).format(*args, **kwds))

def check_value(allowed_values, allow_none=False):
    def validator(value, setting='setting'):
        if allow_none and value is None:
            return
        if value not in allowed_values:
            fail_validation("Expected one of {0!r} for {1}, got {2!r}",
                             allowed_values, setting, value)
    return validator

def check_type(expected_type, allow_none=False):
    def validator(value, setting='setting'):
        if allow_none and value is None:
            return
        if not isinstance(value, expected_type):
            fail_validation("Expected {0!r} for {1}, got {2!r}",
                             expected_type, setting, type(value))
    return validator

def check_text(allow_none=False):
    # Allow either string type for now
    # TODO: Tighten this up to enforce unicode
    #       Means fixing deserialisation interfaces :P
    return check_type(basestring, allow_none)

def check_regex(pattern, expected=None, allow_none=False):
    _validate_text = check_text()
    if expected is None:
        expected = "text matching {0!r}".format(pattern)
    err_msg = "Expected {0} for {{0}}, got {{1!r}}".format(expected)
    def validator(value, setting='setting'):
        if allow_none and value is None:
            return
        _validate_text(value, setting)
        # We use Unicode storage, but stick with the ASCII rules
        # for pattern matching on whitespace etc.
        if re.match(pattern, value) is None:
            fail_validation(err_msg, setting, value)
    return validator

SIMPLE_ID_REGEX = r'^[\w\-]+$'
def check_simple_id(expected='simple ID (alphanumeric, underscores, hyphens)', allow_none=False):
    return check_regex(SIMPLE_ID_REGEX, expected, allow_none)

PULP_ID_REGEX = r'^[_A-Za-z]+$'
def check_pulp_id(expected='valid Pulp ID', allow_none=False):
    return check_regex(PULP_ID_REGEX, expected, allow_none)

VALID_FILTER_REGEX = r'^[][*?@%+=:,./~_\w\-]+$'
def check_rsync_filter(allow_none=False):
    return check_regex(VALID_FILTER_REGEX, 'valid rsync filter', allow_none)

def check_rsync_filter_sequence():
    return check_sequence(check_rsync_filter())


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
            fail_validation("{0!r} must start and end with '/' "
                             "characters, got {1!r}",
                             setting, value)
    return validator

def check_sequence(item_validator, allow_none=False):
    def validator(value, setting='setting'):
        if allow_none and value is None:
            return
        # Check we've been given a sequence
        if isinstance(value, basestring):
            fail_validation("Strings not accepted for {0!r}, got {1!r}",
                              setting, value)
        if hasattr(value, 'keys'):
            fail_validation("Mappings not accepted for {0!r}, got {1!r}",
                              setting, type(value))
        try:
            itr = iter(value)
        except (TypeError, AttributeError):
            fail_validation("Expected sequence for {0!r}, got {1!r}",
                              setting, type(value))
        # Check individual items
        for i, item in enumerate(itr):
            item_setting = setting + "[{0}]".format(i)
            item_validator(item, item_setting)
    return validator

def check_mapping_values(item_validator, allow_none=False):
    seq_validator = check_sequence(item_validator, allow_none)
    def validator(value, setting='setting'):
        seq_validator(value.values(), setting)
    return validator

def check_mapping(spec, allow_none=False):
    def validator(value, setting='setting'):
        if allow_none and value is None:
            return
        # Check we've been given a mapping
        try:
            value_items = value.items()
        except (AttributeError, TypeError):
            fail_validation("Expected mapping for {0}, got {1!r}",
                                setting, type(value))
        # Check for missing and extra attributes
        provided = set(value)
        expected = set(spec)
        missing = expected - provided
        if missing:
            fail_validation("{0!r} missing from {1}, got {2!r}",
                            sorted(missing), setting, value)
        extra = provided - expected
        if extra:
            fail_validation("{0!r} unexpected in {1}, got {2!r}",
                            sorted(extra), setting, value)
        # Check the validation of the individual items
        for key, value in value_items:
            value_setting = setting + "[{0!r}]".format(key)
            checker = spec[key]
            if isinstance(checker, ValidatedConfig):
                checker = checker.check()
            elif isinstance(checker, list):
                checker = check_sequence(checker[0].check())
            checker(value, value_setting)
    return validator

def validate_config(config, spec):
    check_mapping(spec)(config, 'config')

class ValidatedConfig(object):
    _SPEC = {}
    _DEFAULTS = {}

    def __init__(self, config=None):
        self.spec = self._SPEC
        self.config = self._init_config(config)

    def _init_config(self, config):
        if config is None:
            return
        config = config.copy()
        complete = copy.deepcopy(self._DEFAULTS)
        if config is not None:
            # Check for subspecs first
            for key, spec in self._SPEC.items():
                try:
                    value = config.pop(key)
                except KeyError:
                    continue
                if isinstance(spec, ValidatedConfig):
                    complete[key] = spec(value)
                elif isinstance(spec, list):
                    spec = spec[0]
                    complete[key] = [spec(entry) for entry in value]
                else:
                    complete[key] = value
            # Make sure any unexpected values get reported on validation
            complete.update(config)
        return complete

    def __iter__(self):
        return self._SPEC.iterkeys()

    def validate(self):
        validate_config(self.config, self.spec)

    @classmethod
    def check(cls):
        mapping_validator = check_mapping(cls._SPEC)
        def validator(value, setting='setting'):
            if not isinstance(value, cls):
                fail_validation("Expected {0!r} for {1}, got {2!r}",
                                cls, setting, type(value))
            mapping_validator(value.config, setting)
        return validator

    @classmethod
    def ensure_validated(cls, config):
        checked_config = cls(config)
        checked_config.validate()
        return checked_config.config

















