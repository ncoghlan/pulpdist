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

"""shellutil - additional shell utilities (beyond the standard library's shutil)
"""

import fnmatch
import os
import os.path
import collections
import sys
import tempfile
import contextlib
import shutil


# Rough equivalent of the 3.x tempfile.TemporaryDirectory
@contextlib.contextmanager
def temp_dir():
    dirname = tempfile.mkdtemp()
    dirname = os.path.realpath(dirname)
    try:
        yield dirname
    finally:
        shutil.rmtree(dirname)

# Directory walking helper
WalkedDir = collections.namedtuple("WalkedDir", "path subdirs files depth")

def filtered_walk(top, file_pattern=None, dir_pattern=None,
                       excluded_files=None, excluded_dirs=None,
                       depth=None, followlinks=False,
                       onerror=None, onloop=None):
    """filtered_walk is similar to os.walk, but offers the following additional features:
        - yields a named tuple of (path, subdirs, files, depth)
        - allows independent glob-style filters for filenames and subdirectories
        - allows independent exclusion filters for filenames and subdirectories
        - emits a message to stderr and skips the directory if a symlink loop is encountered when following links
        - allows a recursion depth limit to be specified

       Selective walks are always top down, as the directory listings must be altered to provide
       the above features. If not None, depth must be at least 0. A depth of zero can be useful
       to get separate filtered subdirectory and file listings for a given directory.

       onerror is passed to os.walk to handle os.listdir errors
       onloop (if provided) can be used to override the default symbolic loop handling. It is
       called with the directory path as an argument when a loop is detected. Any false return
       value will skip the directory, any true value means the directory will be processed
       as normal.
    """
    if depth is not None and depth < 0:
        msg = "Depth limit must be None or greater than 0 ({!r} provided)"
        raise ValueError(msg.format(depth))
    if onloop is None:
        def onloop(path):
            msg = "Symlink {!r} refers to a parent directory, skipping\n"
            sys.stderr.write(msg.format(path))
            sys.stderr.flush()
    if followlinks:
        real_top = os.path.abspath(os.path.realpath(top))
    sep = os.sep
    initial_depth = top.count(sep)
    for path, walk_subdirs, files in os.walk(top, topdown=True,
                                             onerror=onerror,
                                             followlinks=followlinks):
        # Check for symlink loops
        if followlinks and os.path.islink(path):
            # We just descended into a directory via a symbolic link
            # Check if we're referring to a directory that is
            # a parent of our nominal directory
            relative = os.path.relpath(path, top)
            nominal_path = os.path.join(real_top, relative)
            real_path = os.path.abspath(os.path.realpath(path))
            path_fragments = zip(nominal_path.split(sep), real_path.split(sep))
            for nominal, real in path_fragments:
                if nominal != real:
                    break
            else:
                if not onloop(path):
                    walk_subdirs[:] = []
                    continue
        # Filter files, if requested
        if file_pattern is not None:
            files = fnmatch.filter(files, file_pattern)
        if excluded_files is not None:
            files = [f for f in files
                      if not any(fnmatch.fnmatch(f, pat)
                                  for pat in excluded_files)]
        # We hide the underlying generator's subdirectory list, since we
        # clear it internally when we reach the depth limit (if any)
        if dir_pattern is None:
            subdirs = walk_subdirs[:]
        else:
            subdirs = fnmatch.filter(walk_subdirs, dir_pattern)
        if excluded_dirs is not None:
            subdirs[:] = (d for d in subdirs
                           if not any(fnmatch.fnmatch(d, pat)
                                       for pat in excluded_dirs))
        # Report depth
        current_depth = path.count(sep) - initial_depth
        yield WalkedDir(path, subdirs, files, current_depth)
        # Filter directories and implement depth limiting
        if depth is not None and current_depth >= depth:
            walk_subdirs[:] = []
        else:
            walk_subdirs[:] = subdirs
