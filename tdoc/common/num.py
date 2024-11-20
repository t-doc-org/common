# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import pathlib

from docutils import nodes
from sphinx import errors
from sphinx.util import docutils, logging

from . import __version__

_log = logging.getLogger(__name__)


def setup(app):
    app.add_role('num', Num())
    app.add_enumerable_node(num, 'num', lambda n: True,
                            html=(visit_num, depart_num))
    app.connect('config-inited', update_numfig_format)
    app.connect('env-get-updated', number_per_type, priority=999)
    app.connect('doctree-resolved', update_num_nodes)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class NoNum:
    def __contains__(self, value): return False
    def __mod__(self, other): return ''


def update_numfig_format(app, config):
    # Disable numbering by default for all standard enumerable node types except
    # 'section', and set the default format for 'num'.
    numfig_format = config.numfig_format
    for k in ('code-block', 'figure', 'section', 'table'):
        if numfig_format.setdefault(k, k == 'section') is True:
            del numfig_format[k]
    numfig_format.setdefault('num', '%s')
    for k, v in numfig_format.items():
        if v is False:
            if k == 'section':
                raise errors.ConfigError(
                    f"numfig_format: Numbering cannot be disabled for '{k}'")
            numfig_format[k] = NoNum()


class Num(docutils.ReferenceRole):
    def run(self):
        node = num()
        name = nodes.make_id(self.target)
        if '-' not in name:
            msg = self.inliner.reporter.error(
                f":num: Invalid target (format: TYPE-NAME): {self.target}",
                line=self.lineno)
            prb = self.inliner.problematic(self.rawtext, self.rawtext, msg)
            return [prb], [msg]
        node['names'].append(name)
        self.inliner.document.note_explicit_target(node, node)
        node['title'] = self.title if self.has_explicit_title else '%s'
        return [node], []


class num(nodes.Inline, nodes.TextElement): pass


def number_per_type(app, env):
    # Convert the global numbering to per-type numbering.
    per_type = {}
    for doc, fignums in env.toc_fignumbers.items():
        if (fignums := fignums.get('num')) is None: continue
        for nid, ns in fignums.items():
            typ = nid.split('-', 1)[0]
            *sect, cnt = ns
            per_type.setdefault(typ, {}).setdefault(tuple(sect), []) \
                .append((cnt, nid))
    env.tdoc_nums = nums = {}
    for typ, sects in per_type.items():
        for sect, cnt_nids in sects.items():
            cnt_nids.sort()
            for i, (_, nid) in enumerate(cnt_nids, 1):
                nums[nid] = sect + (i,)
    return []


def update_num_nodes(app, doctree, docname):
    for node, text in iter_num(app.env, doctree, docname):
        del node['title']
        node += [text]

    # TOCs are extracted on doctree-read, as a transform with priority=880,
    # while toc_fignumbers are only assigned later, in env-get-updated. So the
    # num nodes in the TOCs must be updated separately. Replace the node by its
    # text altogether, to avoid duplicate 'id' attributes.
    for node, text in iter_num(app.env, app.env.tocs[docname], docname):
        node.parent.replace(node, text)


def iter_num(env, doctree, docname):
    fail = not env.config.numfig
    for node in doctree.findall(num):
        if fail: raise errors.ConfigError(":num: numfig is disabled")
        n = env.tdoc_nums[node['ids'][0]]
        yield node, nodes.Text(node['title'] % '.'.join(map(str, n)))


def visit_num(self, node):
    self.body.append(self.starttag(node, 'span', suffix=''))


def depart_num(self, node):
    self.body.append('</span>')
