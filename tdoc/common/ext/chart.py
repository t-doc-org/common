# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from sphinx.util import logging

from . import __version__, Dyn, dyn

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('chartjs', ChartJs)
    app.connect('html-page-context', add_css_js)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class ChartJs(Dyn):
    has_content = True
    has_templates = True


def add_css_js(app, page, template, context, doctree):
    if doctree and doctree.next_node(dyn.has_type('chartjs')) is not None:
        app.add_js_file('tdoc/chart.js', type='module')
