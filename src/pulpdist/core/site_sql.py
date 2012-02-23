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
"""SQL definitions for site configuration database definition"""


import sqlite3

SYNC_TYPES = "simple versioned snapshot".split()

INSERT_SYNC_TYPE = """\
INSERT INTO sync_types VALUES (?)
"""

CREATE_SYNC_TYPES = """\
CREATE TABLE sync_types (
    sync_type TEXT PRIMARY KEY
)
"""

CREATE_REMOTE_SETTINGS = """\
CREATE TABLE remote_settings (
    version_suffix TEXT DEFAULT ''
)
"""

CREATE_REMOTE_SERVERS = """\
CREATE TABLE remote_servers (
    server_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    dns TEXT NOT NULL,
    old_daemon INTEGER DEFAULT 0,
    rsync_port INTEGER
)
"""

CREATE_SERVER_PREFIXES = """\
CREATE TABLE server_prefixes (
    server_id TEXT NOT NULL REFERENCES remote_servers,
    local_prefix TEXT NOT NULL
)
"""

CREATE_REMOTE_SOURCES = """\
CREATE TABLE remote_sources (
    source_id TEXT PRIMARY KEY,
    server_id TEXT NOT NULL REFERENCES remote_servers,
    name TEXT NOT NULL,
    remote_path TEXT NOT NULL
)
"""

CREATE_SOURCE_PREFIXES = """\
CREATE TABLE source_prefixes (
    source_id TEXT NOT NULL REFERENCES remote_sources,
    local_prefix TEXT NOT NULL
)
"""

CREATE_REMOTE_TREES = """\
CREATE TABLE remote_trees (
    tree_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES remote_sources,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    tree_path TEXT NOT NULL,
    sync_hours INTEGER,
    sync_type TEXT NOT NULL REFERENCES sync_types,
    excluded_files TEXT DEFAULT '',
    sync_filters TEXT DEFAULT '',
    version_pattern TEXT,
    version_prefix TEXT,
    excluded_versions TEXT DEFAULT '',
    version_filters TEXT DEFAULT '',
    CHECK (version_pattern IS NOT NULL OR version_prefix IS NOT NULL)
)
"""

CREATE_LOCAL_SETTINGS = """\
CREATE TABLE local_settings (
    site TEXT,
    storage_prefix TEXT
)
"""

CREATE_LOCAL_TREES = """\
CREATE TABLE local_trees (
    repo_id TEXT PRIMARY KEY,
    tree_id TEXT NOT NULL REFERENCES remote_trees,
    name TEXT,
    description TEXT,
    tree_path TEXT,
    enabled INTEGER DEFAULT 0,
    dry_run_only INTEGER DEFAULT 0,
    delete_old_dirs INTEGER DEFAULT 0,
    excluded_files TEXT,
    sync_filters TEXT,
    excluded_versions TEXT,
    version_filters TEXT
)
"""


BUILD_DATABASE = (
  CREATE_SYNC_TYPES,
  CREATE_REMOTE_SETTINGS,
  CREATE_REMOTE_SERVERS,
  CREATE_REMOTE_SOURCES,
  CREATE_REMOTE_TREES,
  CREATE_SERVER_PREFIXES,
  CREATE_SOURCE_PREFIXES,
  CREATE_LOCAL_SETTINGS,
  CREATE_LOCAL_TREES,
)

def in_memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    with conn:
        for command in BUILD_DATABASE:
            conn.execute(command)
    with conn:
        for sync_type in SYNC_TYPES:
            conn.execute(INSERT_SYNC_TYPE, [sync_type])
    return conn