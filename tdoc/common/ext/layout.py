# Copyright 2025 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

from sphinx.util import logging

from . import __version__

_log = logging.getLogger(__name__)


def setup(app):
    app.connect('tdoc-html-page-config', set_html_data_attrs)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def set_html_data_attrs(app, page, config, doctree):
    if page is None: return
    md = app.env.metadata[page]
    if (layout := md.get('layout')) is None: return
    if (v := layout.get('print-toc')) == 'hide':
        config['html_data']['tdocHideToc'] = ''
    elif v not in (None, 'show'):
        _log.warning(f"Invalid {{metadata}} layout:print-toc: value: {v}")
