#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Based on pulp-dev.py from Pulp
# symlinks appropriate files directories to allow serving
# a local working copy of pulpdist via httpd

import optparse
import os
import shutil
import sys
import site

DIRS = (
    '/etc/httpd/conf.d',
    '/srv',
    '/var/lib',
    '/var/www/pub/pulpdist',
    '/var/www/pub/pulpdist_sync_logs',
    '/var/log/pulpdist',
)

#
# Str entry assumes same src and dst relative path.
# Tuple entry is explicit (src, dst)
#
LINKS = (
    'etc/pulpdist',
    'etc/httpd/conf.d/pulpdist.conf',
    'srv/pulpdist',
    'var/lib/pulpdist',
)

def parse_cmdline():
    """
    Parse and validate the command line options.
    """
    parser = optparse.OptionParser()

    parser.add_option('-I', '--install',
                      action='store_true',
                      help='install pulpdist development files')
    parser.add_option('-U', '--uninstall',
                      action='store_true',
                      help='uninstall pulpdist development files')
    parser.add_option('-D', '--debug',
                      action='store_true',
                      help=optparse.SUPPRESS_HELP)

    parser.set_defaults(install=False,
                        uninstall=False,
                        debug=False)

    opts, args = parser.parse_args()

    if opts.install and opts.uninstall:
        parser.error('both install and uninstall specified')

    if not (opts.install or opts.uninstall):
        parser.error('neither install or uninstall specified')

    return (opts, args)


def debug(opts, msg):
    if not opts.debug:
        return
    sys.stderr.write('%s\n' % msg)


def create_dirs(opts):
    for d in DIRS:
        debug(opts, 'creating directory: %s' % d)
        if os.path.exists(d) and os.path.isdir(d):
            debug(opts, '%s exists, skipping' % d)
            continue
        os.makedirs(d, 0777)

def get_package_link(opts):
    try:
        site_dir = site.getsitepackages()[0]
    except AttributeError:
        # Assume 2.6 == RHEL6 (or derivative)
        site_dir = '/usr/lib/python2.6/site-packages'
    else:
        if '64' in site_dir:
            site_dir = site.getsitepackages()[1]
    debug(opts, 'site package dir: %s' % site_dir)
    dst = os.path.join(site_dir, 'pulpdist')
    return 'src/pulpdist', dst

def getlinks(opts):
    links = []
    for l in LINKS:
        if isinstance(l, (list, tuple)):
            src = l[0]
            dst = l[1]
        else:
            src = l
            dst = os.path.join('/', l)
        links.append((src, dst))
    links.append(get_package_link(opts))
    return links


def install(opts):
    create_dirs(opts)
    currdir = os.path.abspath(os.path.dirname(__file__))
    for src, dst in getlinks(opts):
        debug(opts, 'creating link: %s' % dst)
        try:
            os.symlink(os.path.join(currdir, src), dst)
        except OSError, e:
            if e.errno != 17:
                raise
            debug(opts, '%s exists, skipping' % dst)
            continue

    # Grant apache write access to the pulp tools log file and pulp 
    # packages dir
    os.system('setfacl -m user:apache:rwx /var/log/pulpdist')
    os.system('setfacl -m user:apache:rwx /var/lib/pulpdist')
    os.system('setfacl -m user:apache:rwx /var/www/pub/pulpdist')
    os.system('setfacl -m user:apache:rwx /var/www/pub/pulpdist_sync_logs')
    # guarantee apache always has write permissions
    os.system('chmod 3775 /var/log/pulpdist')
    os.system('chmod 3775 /var/lib/pulpdist')
    os.system('chmod 3775 /var/www/pub/pulpdist')
    os.system('chmod 3775 /var/www/pub/pulpdist_sync_logs')

    # Disable existing SSL configuration
    #if os.path.exists('/etc/httpd/conf.d/ssl.conf'):
    #    shutil.move('/etc/httpd/conf.d/ssl.conf', '/etc/httpd/conf.d/ssl.off')

    print "Don't forget to run 'python -m pulpdist.manage_site collectstatic'"
    return os.EX_OK


def uninstall(opts):
    for src, dst in getlinks(opts):
        debug(opts, 'removing link: %s' % dst)
        if not os.path.exists(dst):
            debug(opts, '%s does not exist, skipping' % dst)
            continue
        os.unlink(dst)

    # Leaves directories around, oh well...
    return os.EX_OK

# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # TODO add something to check for permissions
    opts, args = parse_cmdline()
    if opts.install:
        sys.exit(install(opts))
    if opts.uninstall:
        sys.exit(uninstall(opts))
