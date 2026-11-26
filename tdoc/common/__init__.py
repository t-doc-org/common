# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from packaging import version as _version

__project__ = 't-doc-common'
__version__ = '1.1'

class Version(_version.Version):
    @property
    def short(self):
        res = self.base_version
        if (p := self.pre) is not None: res += pre[0][:1]
        if self.is_postrelease: res += 'p'
        if self.is_devrelease: res += 'd'
        return res

version = Version(__version__)
