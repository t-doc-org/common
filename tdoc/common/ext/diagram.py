# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from docutils import nodes
from sphinx.util import logging

from . import __version__, Dyn

_log = logging.getLogger(__name__)


def setup(app):
    app.add_config_value('tdoc_mermaid', {}, 'html', dict)
    app.add_directive('mermaid', Mermaid)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class Mermaid(Dyn):
    has_content = True

    def populate(self, node):
        if self.content.count('---') == 1: node.append(nodes.Text("---\n"))
        super().populate(node)
