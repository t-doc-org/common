# Copyright 2026 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import logging as _logging

from sphinx._cli.util import errors as errors
from sphinx.util import logging

from . import patch
from .. import util


_log_exc = _logging.getLogger('tdoc-sphinx-exception')
_log_exc.propagate = False


class WarningHandler(logging.WarningStreamHandler):
    terminator = '\0'

    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(open(path, 'w', encoding='utf-8', errors='replace'))

    def emit_(self, rec):
        self.stream.write(f'{self.format(rec).strip()}\0')


class WarningSuppressor(logging.WarningSuppressor):
    def __init__(self, app):
        # The base class uses app.config and app._warncount. We don't want it to
        # count warnings, because that's already done by a separate instance. So
        # we pass self as app, forward config and provide a dummy _warncount.
        self.app = app
        self._warncount = 0
        super().__init__(self)

    @property
    def config(self): return self.app.config


@patch.patch(logging, 'setup')
def _logging_setup(orig, app, *args, **kwargs):
    res = orig(app, *args, **kwargs)

    # Set up an additional logging handler to capture warnings and above and
    # write them to a file.
    h = WarningHandler(app.outdir.parent / util.build_errors)
    h.addFilter(WarningSuppressor(app))
    h.addFilter(logging.OnceFilter())
    h.setLevel(_logging.WARNING)
    _log_exc.addHandler(h)
    logger = _logging.getLogger(logging.NAMESPACE)
    logger.addHandler(h)
    return res


@patch.patch(errors, 'handle_exception')
def _errors_handle_exception(orig, exc, /, *args, **kwargs):
    import bdb
    if _log_exc.handlers \
            and not isinstance(exc, (KeyboardInterrupt, bdb.BdbQuit)):
        _log_exc.error(f"{exc.__class__.__name__}: {exc}", exc_info=exc)
    return orig(exc, *args, **kwargs)


if __name__ == '__main__':
    import sphinx.__main__  # noqa: E402
