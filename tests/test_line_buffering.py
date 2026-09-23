"""Polysh - Tests - Line Buffering

Copyright (c) 2024 InnoGames GmbH
"""
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import stat
import tempfile
import unittest

import pexpect

from tests import launch_polysh

# A racadm(8) like shell that echoes back the command it was given, in
# fragments slow enough for polysh to see an unfinished line.  This is what
# real iDRACs do, as no stty -echo can be sent to them.
FRAGMENTING_SHELL = '''#!/usr/bin/env python3
import sys
import time

sys.stdout.write('racadm>>')
sys.stdout.flush()
for line in sys.stdin:
    command = line.strip()
    if command == 'exit':
        break
    for piece in (command[:2], command[2:]):
        sys.stdout.write(piece)
        sys.stdout.flush()
        time.sleep(0.4)
    sys.stdout.write('\\r\\nWed Sep 23 19:03:18 2026\\r\\nracadm>>')
    sys.stdout.flush()
'''

# Its last line of output lacks a trailing newline, and then it goes away
UNTERMINATED_SHELL = '''#!/usr/bin/env python3
import sys

sys.stdout.write('racadm>>')
sys.stdout.flush()
for line in sys.stdin:
    if line.strip() == 'exit':
        sys.stdout.write('\\r\\nno newline here')
        sys.stdout.flush()
        break
    sys.stdout.write('\\r\\nracadm>>')
    sys.stdout.flush()
'''


class TestLineBuffering(unittest.TestCase):
    def setUp(self):
        self.shells = []

    def tearDown(self):
        for shell in self.shells:
            os.remove(shell)

    def fake_shell(self, source):
        fd, path = tempfile.mkstemp(prefix='polysh_fake_shell.')
        self.shells.append(path)
        os.write(fd, source.encode())
        os.close(fd)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        return path

    def run_polysh(self, shell, extra_args):
        child = launch_polysh(
            [
                f'--ssh={shell}',
                '--prompt=racadm>>',
                '--no-color',
                '--command=getractime',
                *extra_args,
                'host1',
            ]
        )
        child.expect(pexpect.EOF)
        return child.before

    def testFragmentedWithoutLineBuffering(self):
        shell = self.fake_shell(FRAGMENTING_SHELL)
        output = self.run_polysh(shell, [])
        # By default an unfinished line is printed as soon as the remote goes
        # quiet, so the echoed command is split over two prefixed lines
        self.assertIn('host1 : ge', output)
        self.assertNotIn('host1 : getractime', output)

    def testFragmentedWithLineBuffering(self):
        shell = self.fake_shell(FRAGMENTING_SHELL)
        output = self.run_polysh(shell, ['--line-buffering'])
        self.assertIn('host1 : getractime', output)
        self.assertIn('host1 : Wed Sep 23 19:03:18 2026', output)

    def testShortOption(self):
        shell = self.fake_shell(FRAGMENTING_SHELL)
        output = self.run_polysh(shell, ['-l'])
        self.assertIn('host1 : getractime', output)

    def testLastLineWithoutNewline(self):
        shell = self.fake_shell(UNTERMINATED_SHELL)
        output = self.run_polysh(shell, ['-l'])
        # Held back by line buffering, but flushed when the remote goes away
        self.assertIn('host1 : no newline here', output)
