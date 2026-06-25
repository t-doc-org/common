% Copyright 2026 Remy Blank <remy@c-space.org>
% SPDX-License-Identifier: MIT

# Extension

## Sphinx extensions

t-doc is based on [Sphinx](https://www.sphinx-doc.org/), which provides many
[extension mechanisms](https://www.sphinx-doc.org/en/master/development/) to
add roles and directives or extend the build process. This doesn't require
creating a separate Python package, and can be done within a site repository.

Please refer to the
[Sphinx documentation](https://www.sphinx-doc.org/en/master/development/) to
extend t-doc via Sphinx.

## t-doc extensions

The roles and directives provided by t-doc are intended to cover the most common
use cases. For more specific uses, they provide extension points that can be
used from site repositories to augment their capabilities.

Many roles and directies generate custom `<tdoc-*>` HTML elements that are
rendered asynchronously, so they may not be complete by the time the
`DOMContentLoaded` fires. This section presents two methods for safely
adding functionality to `<tdoc-*>` elements.

The following tables shows how roles and directives map to custom elements.

|Role / directive|Element|Element class|
|---|---|---|
|{rst:dir}`chartjs`|`<tdoc-dyn type="chartjs">`{l=html}|{js:class}`~core.DynElement`|
|{rst:dir}`exec`|`<tdoc-exec>`{l=html}|`ExecElement`|
|{rst:dir}`jsxgraph`|`<tdoc-dyn type="jsxgraph">`{l=html}|{js:class}`~core.DynElement`|
|{rst:dir}`mermaid`|`<tdoc-dyn type="mermaid">`{l=html}|{js:class}`~core.DynElement`|
|{rst:dir}`poll`|`<tdoc-poll>`{l=html}|`PollElement`|
|{rst:dir}`quiz`|`<tdoc-quiz>`{l=html}|`QuizElement`|

### Lifecycle hooks

{js:meth}`TdocElement.extend() <core.TdocElement.[static] extend>` allows
registering a handler object whose methods are called at different stages of the
lifecycle of `<tdoc-*>` elements. In particular, the `ready()` method is called
when t-doc has finished rendering the element.

The following example adds a button to {rst:dir}`exec` blocks having the class
`extend-inspect` that displays the content of the block.

```{exec} html
:class: extend-inspect
:editor:
:reset: hide
:output-style: max-height: 6rem;
<p>This is a paragraph.</p>
<p>This is another paragraph.</p>
```

<script type="module">
const {elmt, on, qs, TdocElement} = await tdoc.import('tdoc/core.js');
TdocElement.extend('tdoc-exec', {
  ready(el) {
    if (!el.classList.contains('extend-inspect')) return;
    const btn = qs(el, '.tdoc-exec-controls').appendChild(
      elmt`<button class="fa-magnifying-glass tdoc"></button>`);
    on(btn).click(() => alert(`The editor content is:\n\n${el.runner.text}`));
  },
});
</script>

### Enumeration

Selected `<tdoc-*>` elements on a page can be enumerated with
{js:func}`~core.qsaReady`. The function waits for the DOM to be loaded and for
the elements to be ready before yielding them asynchronously. The returned
generator must therefore be iterated with `for await`{l=js}.

The following example adds a button to {rst:dir}`exec` blocks having the class
`enum-inspect` that displays the content of the block.

```{exec} html
:class: enum-inspect
:editor:
:reset: hide
:output-style: max-height: 6rem;
<p>This is a paragraph.</p>
<p>This is another paragraph.</p>
```

<script type="module">
const {elmt, on, qs, qsaReady} = await tdoc.import('tdoc/core.js');
for await (const el of qsaReady(document, `tdoc-exec.enum-inspect`)) {
  const btn = qs(el, '.tdoc-exec-controls').appendChild(
    elmt`<button class="fa-magnifying-glass tdoc"></button>`);
  on(btn).click(() => alert(`The editor content is:\n\n${el.runner.text}`));
}
</script>

## JavaScript libraries

### `tdoc/early.js`

This script
([source](https://github.com/t-doc-org/common/blob/main/tdoc/common/static/tdoc/early.js))
is run before most scripts and modules are loaded, and exposes functionality via
the {js:data}`tdoc` object accessible in the global namespace.

{.rubric}
Globals

```{js:data} tdoc
This object is pre-loaded into the global namespace and provides functionality
that is needed outside of JavaScript modules, and therefore cannot be placed
into a module.
```

{.rubric}
Functions

```{js:function} tdoc.import(...modules)
Import one or more JavaScript modules.

:arg !string[] modules: The modules to import, as paths relative to the
`_static` directory.
:returns: A `Promise` resolving to the module namespace if a single argument was
provided, or to an `Array` of module namespaces if multiple arguments were
provided.
```

### `tdoc/core.js`

```{js:module} core
This module
([source](https://github.com/t-doc-org/common/blob/main/tdoc/common/static/tdoc/core.js))
provides functionality used across all of t-doc.
```

{.rubric}
Module globals

```{js:data} domLoaded
A `Promise` that resolves when the DOM content has been fully loaded, i.e. the
`DOMContentLoaded` event has been dispatched on the document.
```

{.rubric}
Functions

```{js:function} qs(el, selector)
An short alias for `el.querySelector(selector)`. It gracefully handles the case
where `el` is `undefined` or `null`.

:arg !HTMLElement|DocumentFragment el: The DOM object to query.
:arg !string selector: A CSS selector.
:returns: The first matching element, or `null` if there are none.
```

```{js:function} qsa(el, selector)
An short alias for `el.querySelectorAll(selector)`. It gracefully handles the
case where `el` is `undefined` or `null` by returning an empty `NodeList`.

:arg !HTMLElement|DocumentFragment el: The DOM object to query.
:arg !string selector: A CSS selector.
:returns: A `NodeList` of elements matching the selector.
```

```{js:function} qsaReady(el, selector)
Query DOM elements below `el` matching `selector` once, and yield them
asynchronously. Standard elements are yielded immediately after the DOM has been
loaded; custom `<tdoc-*>` elements are yielded as they become ready.

:arg !HTMLElement|DocumentFragment el: The DOM object to query.
:arg !string selector: A CSS selector.
:returns: An asynchronous iterator that yields the matching elements.
```

````{js:function} html(tmpl, ...values)
A tag function that safely generates a
[`DocumentFragment`](https://developer.mozilla.org/en-US/docs/Web/API/DocumentFragment)
via a [tagged template](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#tagged_templates).
Substitutions are HTML-escaped, except for `DocumentFragment` and `Element`
instances, whose `outerHTML` is substituted as-is.

```{code-block} js
const value = "x < y";
const el = html`The variable <code>value</code> contains: ${value}`;
```

:returns: A `DocumentFragment`.
````

```{js:function} elmt(tmpl, ...values)
A tag function that safely generates an
[`Element`](https://developer.mozilla.org/en-US/docs/Web/API/Element)
via a [tagged template](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#tagged_templates).
Substitutions are HTML-escaped, except for `DocumentFragment` and `Element`
instances, whose `outerHTML` is substituted as-is.

:returns: The first `Element` parsed from the string.
```

```{js:function} htmle(tmpl, ...values)
A tag function that safely generates an {js:class}`HtmlError` via a
[tagged template](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#tagged_templates).
Substitutions are HTML-escaped, except for `DocumentFragment` and `Element`
instances, whose `outerHTML` is substituted as-is.

:returns: An {js:class}`HtmlError`.
```

````{js:function} on(el)
Return a `Proxy` object that sets event listeners on an element. This is a more
compact way to call `el.addEventListener()`. To set a listener, call the method
on the proxy that corresponds to the event, and pass the listener function as an
argument. The methods return the `Proxy`, so multiple liseteners can be set with
chained calls.

```{code-block} js
on(qs(document, 'button'))
    .click(() => alert("Clicked"))
    .mouseenter(() => alert("Mouse entered"))
    .mouseleave(() => alert("Mouse left"));
```

:arg !HTMLElement el: The DOM element on which to set event listeners.
:returns: A `Proxy` object.
````

```{js:function} showAlert(message, kind = 'success')
Show an alert at the top of the page. If the message is an
{js:class}`HtmlError`, `kind` is taken from the error and defaults to
`'danger'`.

:arg !string|Error message: The message to display.
:arg !string kind: The
[kind](https://getbootstrap.com/docs/5.3/components/alerts/)
of message to display.
```

{.rubric}
Classes

````{js:class} HtmlError(html, options)
An `Error` subclass that carries its message as an HTML element or fragment. It
is useful to generate rich error messages for display e.g. with
{js:func}`showAlert`.

{.rubric}
Methods

```{js:method} [static] of(err)
Create an `HtmlError` from an `Error` or a string.

:arg !Error|string err: The error or error message from which to construct the
`HtmlError`. If `err` is already an `HtmlError`, it is returned unchanged.
```

```{js:method} as(kind)
Specify the kind of alert to show for this error.

:retunrs: The error itself.
```

{.rubric}
Attributes

```{js:attribute} html
The HTML element or fragment provided to the constructor.
```

```{js:attribute} kind
The kind of alert to show for this error.
```
````

````{js:class} TdocElement
The base class for all custom `<tdoc-*>` elements.

{.rubric}
Methods

```{js:method} [static] extend(name, handler)
Extend a custom `<tdoc-*>` element type. This method registers a handler whose
methods are called at different stages of the lifecycle of element instances.

:arg !string name: The name of the custom element type.
:arg !Object handler: An object of lifecycle methods.

The following methods can be defined on `handler`:

  - `ready(el)`: Called when an element becomes ready.
```

{.rubric}
Attributes

```{js:attribute} ready
A `Promise` that resolves to the element when it becomes ready.
```
````

````{js:class} DynElement
The class implementing `<tdoc-dyn>` custom elements. It extends
{js:class}`TdocElement`.

{.rubric}
Attributes

```{js:attribute} type
The type of the directive, contained in the `type` attribute.
```

```{js:attribute} name
The name of the block, contained in the `name` attribute, if the directive
was named.
```

```{js:attribute} args
The arguments provided in the directive content, contained in the `args`
attribute. This is a serialized JSON object.
```

```{js:attribute} controller
The controller object for the element. The type of the controller is specific
to each directive.
```
````
