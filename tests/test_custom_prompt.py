"""Polysh - Tests - Custom Prompt

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

# A racadm(8) like shell: it greets, then prints a prompt without any
# trailing newline and understands nothing of PS1, stty or echo.
FAKE_SHELL = '''#!/usr/bin/env python3
import sys

sys.stdout.write('Dell Remote Access Controller\\r\\nracadm>>')
sys.stdout.flush()
for line in sys.stdin:
    command = line.strip()
    if command == 'exit':
        sys.stdout.write('\\r\\nbye\\r\\n')
        sys.stdout.flush()
        break
    sys.stdout.write('\\r\\nout[%s]\\r\\nracadm>>' % command)
    sys.stdout.flush()
'''

# Same, but it does not know about exit, so polysh has to give up on it
FAKE_SHELL_NO_EXIT = FAKE_SHELL.replace("command == 'exit'", 'False')


class TestCustomPrompt(unittest.TestCase):
    def setUp(self):
        self.shells = []

    def tearDown(self):
        for shell in self.shells:
            os.remove(shell)

    def fake_shell(self, source=FAKE_SHELL):
        fd, path = tempfile.mkstemp(prefix='polysh_fake_shell.')
        self.shells.append(path)
        os.write(fd, source.encode())
        os.close(fd)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        return path

    def testInteractive(self):
        shell = self.fake_shell()
        child = launch_polysh(
            [
                f'--ssh={shell}',
                '--prompt=racadm>>',
                '--no-color',
                'host1',
                'host2',
            ]
        )
        child.expect(r'ready \(2\)> ')
        child.sendline('getsysinfo')
        child.expect(r'host1 : out\[getsysinfo\]')
        child.expect(r'host2 : out\[getsysinfo\]')
        child.expect(r'ready \(2\)> ')
        child.sendline('exit')
        child.expect(pexpect.EOF)

    def testNonInteractive(self):
        shell = self.fake_shell()
        child = launch_polysh(
            [
                f'--ssh={shell}',
                '--prompt=racadm>>',
                '--no-color',
                '--command=getsysinfo',
                'host1',
            ]
        )
        child.expect(pexpect.EOF)
        output = child.before
        self.assertIn('host1 : out[getsysinfo]', output)
        self.assertIn('host1 : bye', output)
        # The prompt itself is never reported as remote output
        self.assertNotIn('racadm>>', output)

    def testRemoteIgnoringExit(self):
        shell = self.fake_shell(FAKE_SHELL_NO_EXIT)
        child = launch_polysh(
            [
                f'--ssh={shell}',
                '--prompt=racadm>>',
                '--no-color',
                '--command=getsysinfo',
                'host1',
            ]
        )
        child.expect(pexpect.EOF)
        output = child.before
        self.assertIn('host1 : out[getsysinfo]', output)
        self.assertNotIn('racadm>>', output)

    def testBadRegexp(self):
        child = launch_polysh(['--prompt=racadm(>>', 'host1'])
        child.expect('error: invalid --prompt regex')
        child.expect(pexpect.EOF)
