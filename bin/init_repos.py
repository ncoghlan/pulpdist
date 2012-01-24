#!/usr/bin/env python
"""Initialise a Pulp instance with repos based on a JSON config"""
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
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.\

import json
from pulpdist.core.pulpapi import PulpServerClient

if __name__ == "__main__":
    import sys
    pulp_host, repo_fname = sys.argv[1:]
    # Must have already saved credentials with "pulp-admin auth login"
    server = PulpServerClient(pulp_host)
    with open(repo_fname) as repo_file:
        repo_list = json.load(repo_file)
    for repo_details in repo_list:
        repo_id = repo_details["repo_id"]
        server.create_repo(repo_id,
                           repo_details["display_name"],
                           repo_details.get("description", None),
                           repo_details.get("notes", None))
        server.add_importer(repo_id,
                            repo_details["importer_type_id"],
                            repo_details["importer_config"])
        print (server.get_repo(repo_id))
