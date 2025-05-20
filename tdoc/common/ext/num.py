# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from docutils import nodes
from sphinx import errors
from sphinx.environment import collectors
from sphinx.util import docutils, logging, nodes as sphinx_nodes

from . import __version__

_log = logging.getLogger(__name__)


def setup(app):
    app.add_role('num', Num())
    app.add_enumerable_node(num, 'num', lambda n: '<num_title>',
                            html=(visit_num, depart_num))
    app.connect('config-inited', update_numfig_format)
    app.connect('builder-inited', NumCollector.init)
    app.add_env_collector(NumCollector)
    app.connect('env-get-updated', number_per_namespace, priority=501)
    app.connect('doctree-resolved', update_num_nodes)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class NoNum:
    def __contains__(self, value): return False
    def __mod__(self, other): return ''
    def __str__(self): return 'NoNum'
    def __eq__(self, other): return isinstance(other, NoNum)
    def __ne__(self, other): return not isinstance(other, NoNum)

no_num = NoNum()


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
            numfig_format[k] = no_num


class Num(docutils.ReferenceRole):
    def run(self):
        node = num()
        self.set_source_info(node)
        node['target'] = self.target
        node['title'] = self.title if self.has_explicit_title else '%s'
        if ':' in self.target:
            node['names'].append(self.target)
            self.inliner.document.note_explicit_target(node, node)
        else:
            node['ids'].append(sphinx_nodes.make_id(
                self.env, self.inliner.document, self.target))
        return [node], []


class num(nodes.Inline, nodes.TextElement): pass

# Numbering is global per enumerable node type, and we want per-namespace
# numbering. Numbers are assigned in TocTreeCollector.assign_figure_numbers()
# and immediately compared to the old assignment to invalidate documents,
# and there is no opportunity to modify the numbers between assignment and
# comparison.
#
# We wrap the counters in Cnt instances, which compare equal to all integers, so
# that they aren't taken into account for the invalidation in TocTreeCollector.
# Then, after TocTreeCollector has completed, we update the counter values and
# perform invalidation separately.

class Cnt(int):
    def __eq__(self, other): return isinstance(other, int)
    def __ne__(self, other): return not isinstance(other, int)


class NumCollector(collectors.EnvironmentCollector):
    @staticmethod
    def init(app):
        if not hasattr(app.env, 'tdoc_nums'):
            app.env.tdoc_nums = {}  # docname => id => target
        # Save the old num fignumbers for the invalidation check.
        app.env.tdoc_old_num_fignumbers = {
            doc: nfn for doc, fn in app.env.toc_fignumbers.items()
            if (nfn := fn.get('num')) is not None}

    def clear_doc(self, app, env, docname):
        env.tdoc_nums.pop(docname, None)

    def merge_other(self, app, env, docnames, other):
        for docname in docnames:
            env.tdoc_nums[docname] = other.tdoc_nums[docname]

    def process_doc(self, app, doctree):
        nums = app.env.tdoc_nums[app.env.docname] = {}
        for node in doctree.findall(num):
            nums[node['ids'][0]] = node['target']


def number_per_namespace(app, env):
    # Convert the global numbering to per-namespace numbering.
    per_ns = {}
    for doc, fignums in env.toc_fignumbers.items():
        if (fignums := fignums.get('num')) is None: continue
        nums = env.tdoc_nums[doc]
        for nid, n in fignums.items():
            ns = nums[nid].split(':', 1)[0]
            *sect, cnt = n
            per_ns.setdefault(ns, {}).setdefault(tuple(sect), []) \
                .append((cnt, doc, nid))
    for ns, sects in per_ns.items():
        for sect, cnt_nids in sects.items():
            cnt_nids.sort()
            for i, (cnt, doc, nid) in enumerate(cnt_nids, 1):
                env.toc_fignumbers[doc]['num'][nid] = (*sect, Cnt(i))

    # Invalidate docs for which num fignumbers have changed. The section part
    # has already been checked by TocTreeCollector, so we only need to compare
    # the counter part.
    old = env.tdoc_old_num_fignumbers
    del env.tdoc_old_num_fignumbers
    rewrite = []
    for doc, fignums in env.toc_fignumbers.items():
        if not fignums_equal(fignums.get('num'), old.get(doc)):
            rewrite.append(doc)
    return rewrite


def fignums_equal(lhs, rhs):
    if lhs is None or rhs is None: return lhs == rhs
    if len(lhs) != len(rhs): return False
    for nid, ln in lhs.items():
        if (rn := rhs.get(nid)) is None: return False
        if int(ln[-1]) != int(rn[-1]): return False
    return True


def update_num_nodes(app, doctree, docname):
    for node, text in iter_num(app.env, doctree, docname):
        del node['title']
        if node['names']:
            node += [text]
        else:  # Not an explicit target; replace node with its text
            node.parent.replace(node, text)

    # TOCs are extracted on doctree-read, as a transform with priority=880,
    # while toc_fignumbers are only assigned later, in env-get-updated. So the
    # num nodes in the TOCs must be updated separately. Replace the node by its
    # text altogether, to avoid duplicate 'id' attributes.
    for node, text in iter_num(app.env, app.env.tocs[docname], docname):
        node.parent.replace(node, text)


def iter_num(env, doctree, docname):
    fail = not env.config.numfig
    for node in doctree.findall(num):
        if fail: raise errors.ConfigError("{num}: numfig is disabled")
        try:
            n = env.toc_fignumbers[docname]['num'][node['ids'][0]]
        except KeyError:
            _log.warning("The {num} role cannot be used in orphaned documents",
                         location=node)
            continue
        yield node, nodes.Text(node['title'] % '.'.join(map(str, n)))


def visit_num(self, node):
    self.body.append(self.starttag(node, 'span', suffix=''))


def depart_num(self, node):
    self.body.append('</span>')
