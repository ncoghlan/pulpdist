.. pulpdist documentation master file, created by
   sphinx-quickstart on Tue Nov  8 13:10:18 2011.

PulpDist - Filtered Mirroring with Pulp
=======================================

PulpDist is a set of Pulp_ plugins and an associated Django_ application that
together allow a network of Pulp_ servers to be used as a filtered mirroring
network with robust access control mechanisms.

The project is in a usable state for the specific task of filtered mirroring
with rsync, but still has quite a few rough edges. In particular, it still
relies on the alpha version of the plugin APIs in Pulp v1 rather than using
the updated version that are coming in Pulp v2.

Contents:

.. toctree::
   :maxdepth: 2
   :numbered:

   architecture.rst
   webapp.rst
   cli.rst
   plugins.rst
   configuration.rst
   api.rst
   about.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _Pulp: http://pulpproject.org/
.. _Django: http://djangoproject.com/
