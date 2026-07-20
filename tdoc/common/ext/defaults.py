# Copyright 2024 Remy Blank <remy@c-space.org>
# SPDX-License-Identifier: MIT

import types

from docutils.parsers import rst
from docutils.parsers.rst import directives
from sphinx.util import docutils, logging

from . import __version__, merge_dict, patch, report_exceptions

_log = logging.getLogger(__name__)


def setup(app):
    app.add_directive('defaults', Defaults)
    app.add_config_value('tdoc_directive_defaults', {}, 'env', dict)
    app.connect('config-inited', set_config_defaults)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


_directive_defaults = {
    'toctree': {'maxdepth': 1},
}

def set_config_defaults(app, config):
    merge_dict(config.tdoc_directive_defaults, _directive_defaults,
               override=False)


@patch.patch(directives, 'directive')
def _directives_directive(orig, name, language, document):
    name = name.lower()
    cls, msgs = orig(name, language, document)
    if cls is None or is_patched(cls): return cls, msgs
    # Convert old-style directives, updating the directive cache.
    if isinstance(cls, (types.FunctionType, types.MethodType)):
        cls = directives._directives[name] = rst.convert_directive_function(cls)
    # Patch only directive classes referenced by tdoc_directive_defaults.
    # {defaults} patches those it references.
    defs = document.settings.env.app.config.tdoc_directive_defaults
    if (opts := defs.get(name)) is None: return cls, msgs
    if unknown := set(opts) - set(cls.option_spec):
        document.reporter.error(
            f"Unknown options for {{{name}}} directive in "
            f"tdoc_directive_defaults: {", ".join(sorted(unknown))}")
        return cls, msgs
    patch_directive(cls)
    return cls, msgs


def is_patched(cls):
    return hasattr(cls, '_tdoc_defaults_patched')


def patch_directive(cls):
    # Monkey-patch the directive's run() method to set default option
    # values before running the directive.
    def run(self):
        env = self.state.document.settings.env
        for defs in [env.current_document.get('tdoc_defaults', {}),
                     env.app.config.tdoc_directive_defaults]:
            for k, v in defs.get(self.name, {}).items():
                self.options.setdefault(k, self.option_spec[k](v))
        return orig_run(self)
    orig_run, cls.run, cls._tdoc_defaults_patched = cls.run, run, True


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

        # Check option names.
        if unknown := set(self.options) - set(cls.option_spec):
            raise Exception(
                f"{{defaults}}: Unknown options for {{{name}}} directive: "
                f"{", ".join(sorted(unknown))}")

        # Patch the directive.
        if not is_patched(cls): patch_directive(cls)

        # Store the defaults.
        self.env.current_document.setdefault('tdoc_defaults', {})[name] = \
            self.options
        return []
