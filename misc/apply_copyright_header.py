#!/usr/bin/env python
"""Add a copyright header to all Python files in a directory"""
import os
import fnmatch
import codecs
import python_source

HEADER = """
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
""".split("\n")

def _make_parser():
    parser = argparse.ArgumentParser(description='Add copyright headers')
    parser.add_argument('source_dirs', metavar='DIR', type=str, nargs='+',
                    help='a directory to be updated')
    parser.add_argument('--exclude', dest='excluded_dirs', action='append',
                    help='a directory to omit from the update')
    return parser


def add_headers(source_dirs, excluded_dirs=None):
    for source_dir in source_dirs:
        for dirpath, subdirs, files in os.walk(source_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(dirpath, fname)
                with python_source.open_py(fpath) as f:
                    encoding = f.encoding
                    data = f.readlines()
                if not data: # Leave empty __init__.py files alone
                    continue
                for index, line in enumerate(data):
                    if line.startswith("#!"): continue
                    if "coding" in line: continue
                    break

                stable_header = HEADER[2:] # Skip the line with the date in it
                stable_start = index+2
                end = stable_start+len(stable_header)
                if data[stable_start:end] == stable_header:
                    print "Existing header in {}, updating".format(fpath)
                    data[index:stable_start] = HEADER[:2]
                else:
                    print "Adding header to {}".format(fpath)
                    data[index:index] = HEADER
                with codecs.open(fpath, 'w', encoding=encoding):
                    f.writelines(data)
            if excluded_dirs:
                subdirs[:] = [d for d in subdirs if not
                    any(fnmatch.fnmatch(d, pat) for pat in excluded_dirs)]

if __name__ == "__main__":
    import argparse
    args = _make_parser().parse_args()
    add_headers(args.source_dirs, args.excluded_dirs)
    