# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import copy
import yaml

from docutils import nodes
import pyjson5
from sphinx.util import docutils, logging

from . import __version__, merge_dict, report_exceptions

_log = logging.getLogger(__name__)


def setup(app):
    app.add_config_value('metadata', {}, 'html', dict)
    app.add_node(metadata)
    app.add_directive('metadata', Metadata)
    app.connect('doctree-read', extract_metadata)
    app.connect('html-page-context', add_head_elements)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


parsers = {
    'json': lambda s: pyjson5.decode(f'{{{s}}}'),
    'yaml': yaml.safe_load,
}


class metadata(nodes.Element): pass


class Metadata(docutils.SphinxDirective):
    optional_arguments = 1
    has_content = True

    @report_exceptions
    def run(self):
        fmt = self.arguments[0] if self.arguments else 'yaml'
        if (parse := parsers.get(fmt)) is None:
            raise Exception(f"{{metadata}} Invalid format: {fmt}")
        node = metadata(attrs=parse(''.join(f'{ln}\n' for ln in self.content)))
        self.set_source_info(node)
        return [node]


def extract_metadata(app, doctree):
    md = merge_dict(app.env.metadata[app.env.docname], app.config.metadata)
    nodes = list(doctree.findall(metadata))
    for i, node in enumerate(nodes):
        if i == 0:
            if (attrs := node['attrs']) is not None: merge_dict(md, attrs)
        else:
            _log.warning("More than one {metadata} directive in the document",
                         location=node)
        node.parent.remove(node)


def add_head_elements(app, page, template, context, doctree):
    md = app.env.metadata[page]
    add_head_files(app.add_css_file, md.get('styles', []))
    add_head_files(app.add_js_file, md.get('scripts', []))


def add_head_files(add, entries):
    for entry in entries:
        if isinstance(entry, str):
            add(entry, priority=900)
        else:
            kwargs = dict(entry)
            path = kwargs.pop('src', None)
            for k, v in kwargs.items():
                if v is None: kwargs[k] = ''
            add(path, priority=900, **kwargs)
