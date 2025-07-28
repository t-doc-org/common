# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import datetime
import markupsafe

from sphinx.util import logging

from . import __version__

_log = logging.getLogger(__name__)


def setup(app):
    app.connect('html-page-context', set_html_context)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def set_html_context(app, page, template, context, doctree):
    md = app.env.metadata[page]
    if v := md.get('print-styles'): app.add_css_file(v)

    attrs = context['html_attrs']
    if v := app.config.author: attrs['data-tdoc-author'] = v
    attrs['data-tdoc-date'] = datetime.datetime.now().strftime('%Y-%m-%d')
    if v := md.get('subject'): attrs['data-tdoc-subject'] = v
    if context and (v := context.get('title')):
        attrs['data-tdoc-title'] = markupsafe.Markup(v).striptags()
