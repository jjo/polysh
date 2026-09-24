"""Polysh - Library Entry Point

Copyright (c) 2006 Guillaume Chazarain <guichaz@gmail.com>
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

def _read_version() -> tuple:
    """Take the version from the installed package metadata.

    It used to be a literal here, which silently drifted away from
    pyproject.toml and had polysh reporting 0.15 to sentry at version 1.0.5.
    Numeric components become ints, anything else (a pre-release suffix) is
    left as a string.
    """
    fallback = (1, 0, 6)
    try:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as installed_version
    except ImportError:
        # Python older than 3.8
        return fallback
    try:
        raw = installed_version('polysh')
    except PackageNotFoundError:
        # Running from a source tree with no metadata installed
        return fallback
    return tuple(p if not p.isdigit() else int(p) for p in raw.split('.'))


VERSION = _read_version()
