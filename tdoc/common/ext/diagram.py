# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from docutils import nodes
from sphinx.util import logging

from .. import ext

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('mermaid', Mermaid)
    return ext.setup_result


class Mermaid(ext.Dyn):
    has_content = True

    def populate(self, node):
        if self.content.count('---') == 1: node.append(nodes.Text("---\n"))
        node.append(nodes.Text(''.join(f'{line}\n'
                                       for line in self.content)))
