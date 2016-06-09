#!/usr/bin/env python
#
# tests utils.py
#
# Copyright 2014 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import errno
import logging
import os
from subprocess import PIPE

import unittest
from unittest.mock import patch

from bundleplacer.utils import get_command_output


log = logging.getLogger('bundleplacer.test_utils')

DATA_DIR = os.path.join(os.path.dirname(__file__), 'files')


@patch('bundleplacer.utils.os.environ')
@patch('bundleplacer.utils.Popen')
class TestGetCommandOutput(unittest.TestCase):

    def test_get_command_output_timeout(self, mock_Popen, mock_env):
        mock_env.copy.return_value = {'FOO': 'bazbot'}
        mock_Popen.return_value.communicate.return_value = (bytes(), bytes())
        get_command_output("fake", timeout=20)
        mock_Popen.assert_called_with("timeout 20s fake", shell=True,
                                      stdout=PIPE, stderr=PIPE,
                                      bufsize=-1,
                                      env={'LC_ALL': 'C',
                                           'FOO': 'bazbot'},
                                      close_fds=True)

    def test_get_command_output_user_sudo(self, mock_Popen, mock_env):
        mock_env.copy.return_value = {'FOO': 'bazbot'}
        outb, errb = bytes('out', 'utf-8'), bytes('err', 'utf-8')
        mock_Popen.return_value.communicate.return_value = (outb, errb)
        mock_Popen.return_value.returncode = 4747
        with patch('bundleplacer.utils.install_user') as mock_install_user:
            mock_install_user.return_value = 'fakeuser'
            rv = get_command_output("fake", user_sudo=True)
            self.assertEqual(rv, dict(output='out', err='err',
                                      status=4747))

        mock_Popen.assert_called_with("sudo -E -H -u fakeuser fake",
                                      shell=True,
                                      stdout=PIPE, stderr=PIPE,
                                      bufsize=-1,
                                      env={'LC_ALL': 'C',
                                           'FOO': 'bazbot'},
                                      close_fds=True)

    def test_get_command_output_raises(self, mock_Popen, mock_env):
        err = OSError()
        err.errno = errno.ENOENT
        mock_Popen.side_effect = err
        rv = get_command_output('foo')
        self.assertEqual(rv, dict(ret=127, output="", err=""))

        mock_Popen.side_effect = OSError()
        with self.assertRaises(OSError):
            get_command_output('foo')
