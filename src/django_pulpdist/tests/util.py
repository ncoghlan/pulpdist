"""Utility functions for Django Pulp UI unit tests"""

import mock
from .. import models

# We make it easy to mock pulpapi in the models file
# so we don't need a live Pulp server for the unit tests.
# The Pulp Web UI integration tests take care of checking
# how well we align with the *real* server API.
def patch_pulpapi():
    """Mock out pulpapi in the django_pulpdist models file"""
    name = models.__name__ + '.pulpapi'
    return mock.patch(name)
