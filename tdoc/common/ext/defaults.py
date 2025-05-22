# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import types

from docutils.parsers.rst import directives
from sphinx.util import docutils, logging

from . import __version__, report_exceptions

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('defaults', Defaults)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


class DefaultsOpts(dict):
    def __bool__(self): return True
    def __contains__(self, k): return True
    def __getitem__(self, k): return lambda v: v


class Defaults(docutils.SphinxDirective):
    required_arguments = 1
    option_spec = DefaultsOpts()
    has_content = False

    @report_exceptions
    def run(self):
        # Find the directive class.
        name = self.arguments[0].lower()
        cls, msgs = directives.directive(name, self.state.memo.language,
                                         self.state.document)
        if cls is None:
            raise Exception(f"{{defaults}}: Unknown directive: {name}")
        if isinstance(cls, (types.FunctionType, types.MethodType)):
            raise Exception(
                f"{{defaults}}: Unsupported function-type directive: {name}")

        # Check option names.
        if unknown := set(self.options) - set(cls.option_spec):
            raise Exception(
                f"{{defaults}}: Unknown options for {{{name}}} directive: "
                f"{", ".join(sorted(unknown))}")

        # Monkey-patch the directive's run() method to set default option
        # values before running the directive.
        if not cls.__dict__.get('_tdoc_defaults_patched'):
            def run(self):
                env = self.state.document.settings.env
                defaults = env.temp_data.get('tdoc_defaults', {}).get(name, {})
                for k, v in defaults.items():
                    self.options.setdefault(k, self.option_spec[k](v))
                return orig_run(self)
            orig_run, cls.run, cls._tdoc_defaults_patched = cls.run, run, True

        # Store the defaults.
        self.env.temp_data.setdefault('tdoc_defaults', {})[name] = self.options
        return []
