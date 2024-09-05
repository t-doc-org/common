# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib
import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.metadata.plugin.interface import MetadataHookInterface

LICENSES = 'LICENSES.deps.txt'


class MetadataHook(MetadataHookInterface):

    def update(self, metadata):
        # Write an empty LICENSES file to avoid that hatchling complains. It
        # will be generated below.
        root = pathlib.Path(self.root)
        (root / 'LICENSES.deps.txt').write_bytes(b'')


class BuildHook(BuildHookInterface):

    def initialize(self, version, build_data):
        self.app.display_info("Installing node packages")
        self.run(['npm', 'install'])
        self.app.display_info("Removing generated files")
        root = pathlib.Path(self.root)
        for path in root.glob('tdoc/common/static/*.gen.*'):
            path.unlink()
        (root / LICENSES).unlink(missing_ok=True)
        self.app.display_info("Generating files")
        self.run(['npm', 'run', 'build'])

    def run(self, args):
        res = subprocess.run(args, cwd=self.root, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
        if res.returncode != 0:
            self.app.abort(f"Command failed:\n{res.stdout}")
