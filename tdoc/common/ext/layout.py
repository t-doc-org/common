# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import datetime

from sphinx.util import logging

from . import __version__

_log = logging.getLogger(__name__)


def setup(app):
    app.connect('html-page-context', set_html_context)
    app.connect('tdoc-html-page-config', set_html_data_attrs)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def set_html_context(app, page, template, context, doctree):
    md = app.env.metadata[page]
    if v := md.get('print-styles'): app.add_css_file(v)


def set_html_data_attrs(app, page, config, doctree, context):
    if page is None: return
    html_data = config['html_data']
    html_data['tdocAuthor'] = app.config.author
    html_data['tdocDate'] = datetime.datetime.now().strftime('%Y-%m-%d')
    md = app.env.metadata[page]
    if v := md.get('subject'): html_data['tdocSubject'] = v
    if context and (v := context.get('title')): html_data['tdocTitle'] = v
