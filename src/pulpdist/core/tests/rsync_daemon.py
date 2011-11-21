# -*- coding: utf-8 -*-
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
"""Helper to run up an rsync daemon instance on a free port"""

import tempfile
import shutil
import subprocess
import os
import os.path
import socket
import time
import contextlib

# Running a local rsync daemon for testing
#   Port = assigned by OS
#   Create a new temporary directory

config_template = """
pid file = {pid_path}
port = {port}

[test_data]
  path = {test_data_path}
  comment = Data for test purposes
  read only = true
  hosts allow = localhost
  use chroot = false
"""

def _get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("",0))
    port = s.getsockname()[1]
    s.close()
    return port


class RsyncDaemon(object):
    def __init__(self, dir_layout, filenames):
        self.port = port = _get_open_port()
        self.tmp_dir = tmp_dir = tempfile.mkdtemp()
        self.rsync_dir = rsync_dir = os.path.join(tmp_dir, "rsync_data")
        self.data_dir = data_dir = os.path.join(tmp_dir, "test_data")
        self.pid = None
        self._create_test_data(dir_layout, filenames)

    def _create_test_data(self, dir_layout, filenames):
        base_dir = self.data_dir
        for data_dir in dir_layout:
            dpath = os.path.join(base_dir, data_dir)
            os.makedirs(dpath)
            for fname in filenames:
                fpath = os.path.join(dpath, fname)
                with open(fpath, 'w') as f:
                    f.write("GSv3 test data!\n")
                # print("Created {!r})".format(fpath))

    @contextlib.contextmanager
    def _wait_for_pid_file(self, pid_path):
        # We give the rsync server a couple of seconds to start
        start = time.time()
        max_delay = 2
        while time.time() - start < max_delay:
            try:
                f = open(pid_path)
            except IOError:
                pass
            else:
                with f:
                    yield f
                break
            time.sleep(0.01)

    def start(self):
        rsync_dir = self.rsync_dir
        os.makedirs(rsync_dir)
        pid_path = os.path.join(rsync_dir, "rsyncd.pid")
        rsync_config_path = os.path.join(rsync_dir, "rsyncd.conf")
        with open(rsync_config_path, 'w') as f:
            config = config_template.format(pid_path=pid_path,
                                            port=self.port,
                                            test_data_path=self.data_dir)
            f.write(config)

        config_option = "--config={}".format(rsync_config_path)
        command = ["rsync", "--daemon", "-v", config_option]
        # print command
        if subprocess.call(command) == 0:
            with self._wait_for_pid_file(pid_path) as f:
                self.pid = int(f.read().strip())

    def close(self):
        if self.pid is not None:
            subprocess.call(["kill", str(self.pid)])
            self.rsync_pid = None
        shutil.rmtree(self.tmp_dir)
        self.tmp_dir = None

