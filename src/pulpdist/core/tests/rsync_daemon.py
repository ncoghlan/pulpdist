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
    def __init__(self, make_layout):
        self.port = port = _get_open_port()
        self.tmp_dir = tmp_dir = tempfile.mkdtemp().decode("utf-8")
        self.rsync_dir = rsync_dir = os.path.join(tmp_dir, "rsync_data")
        self.data_dir = data_dir = os.path.join(tmp_dir, "test_data")
        self.pid = None
        make_layout(self.data_dir)

    @contextlib.contextmanager
    def _wait_for_pid_file(self, pid_path):
        # We give the rsync server a couple of seconds to start
        start = time.time()
        max_delay = 5
        while time.time() - start < max_delay:
            try:
                f = open(pid_path)
            except IOError:
                pass
            else:
                with f:
                    pid_text = f.read().strip()
                    if pid_text:
                        yield pid_text
                break
            time.sleep(0.01)
        else:
            raise RuntimeError("timeout waiting for rsync server to start")

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

        config_option = "--config={0}".format(rsync_config_path)
        command = ["rsync", "--daemon", "-v", config_option]
        # print command
        if subprocess.call(command) == 0:
            with self._wait_for_pid_file(pid_path) as pid_text:
                self.pid = int(pid_text)
        else:
            raise RuntimeError("rsync server failed to start")

    def close(self):
        if self.pid is not None:
            subprocess.call(["kill", str(self.pid)])
            self.rsync_pid = None
        shutil.rmtree(self.tmp_dir)
        self.tmp_dir = None

