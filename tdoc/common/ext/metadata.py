# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import copy
import yaml

from docutils import nodes
from docutils.parsers.rst import directives
import pyjson5
from sphinx.util import docutils, logging

from . import __version__, merge_dict, report_exceptions

_log = logging.getLogger(__name__)


def setup(app):
    app.add_config_value('metadata', {}, 'env', dict)
    app.add_node(metadata, html=(visit_metadata, None))
    app.add_directive('metadata', Metadata)
    # Set the base metadata before MetadataCollector.
    app.connect('doctree-read', set_base_metadata, priority=499)
    app.connect('env-updated', extract_metadata)
    app.connect('html-page-context', add_head_elements)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class metadata(nodes.Element): pass

def visit_metadata(self, node): raise nodes.SkipNode()


parsers = {
    'json': lambda s: pyjson5.decode(f'{{{s}}}'),
    'yaml': yaml.safe_load,
}


class Metadata(docutils.SphinxDirective):
    optional_arguments = 1
    has_content = True
    option_spec = {
        'recursive': directives.flag,
    }

    @report_exceptions
    def run(self):
        fmt = self.arguments[0] if self.arguments else 'yaml'
        if (parse := parsers.get(fmt)) is None:
            raise Exception(f"{{metadata}} Invalid format: {fmt}")
        node = metadata(attrs=parse(''.join(f'{ln}\n' for ln in self.content)),
                        recursive='recursive' in self.options)
        self.set_source_info(node)
        return [node]


def set_base_metadata(app, doctree):
    # Apply base metadata from config.
    merge_dict(app.env.metadata[app.env.docname], app.config.metadata)


def extract_metadata(app, env):
    # The metadata computation (and therefore the change detection) isn't 100%
    # accurate for incremental builds. Added and modified entries in parent
    # pages are detected correctly, but removed entries may not. Full builds are
    # always fine.
    # TODO: Make incremental builds 100% accurate (similar to num.py)
    prev_metadata = copy.deepcopy(env.metadata)

    # Apply recursive metadata from parent pages.
    def apply_recursive(docname, parent_attrs):
        if parent_attrs: merge_dict(env.metadata[docname], parent_attrs)
        if not (children := env.toctree_includes.get(docname)): return

        attrs = copy.deepcopy(parent_attrs)
        for node in env.get_doctree(docname).findall(
                lambda n: isinstance(n, metadata) and n['recursive']):
            if (v := node['attrs']) is not None: merge_dict(attrs, v)
        for child in children: apply_recursive(child, attrs)

    apply_recursive(app.config.root_doc, {})

    # Apply the pages' own metadata.
    for docname in env.found_docs:
        md = env.metadata[docname]
        for node in env.get_doctree(docname).findall(metadata):
            if (v := node['attrs']) is not None: merge_dict(md, v)

    # Force a rebuild of pages whose metadata has changed.
    return [docname for docname, md in env.metadata.items()
            if md != prev_metadata.get(docname)]


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
