PulpDist Architecture
=====================

PulpDist uses the Pulp repository management utilities to manage
arbitrary directory trees (note that the underlying Pulp features
it uses are under active development, so it still has quite a
long way to go before it can be considered ready for production
use beyond a very narrow set of use cases).

Each site in the mirror network has its own Pulp server. These
servers handle the actual data transfers involved in the mirror
network using a number of custom :ref:`Pulp plugins <pulp-plugins>`.

The status of these transfers can then be monitored using a central
:ref:`web application <web-application>` which uses OAuth to retrieve
information from each Pulp server in the network.

