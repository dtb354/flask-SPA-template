# TaskFlow — Flask + vanilla-JS SPA-style template

A small Flask app that feels like a single-page app — tab navigation,
in-place content swaps, working browser back/forward — without a
frontend framework or a build step. All rendering happens server-side
with Jinja; a ~80-line JavaScript file ([static/app.js](static/app.js))
does the client-side wiring.

This document explains the mechanics of that navigation and how to
extend the template with your own pages and actions.

## Running it

```bash
python app.py
```

Open `http://127.0.0.1:5001` (redirects to `/tasks`). Runs with
`debug=True`, so editing a Python or template file auto-reloads the
server. Editing `static/app.js` just needs a browser refresh.

There's no build step and no `requirements.txt` — the only dependency
is Flask itself.

## The core idea: one route, two renderings

Every "page" route (`/tasks`, `/completed`, `/stats`, `/about`) can be
requested two different ways:

1. **A hard load** — the user types the URL or hits refresh. The
   browser needs a complete HTML document.
2. **An in-app navigation** — the user clicked a tab or a button.
   The page already has the shell (nav bar, `<head>`, etc.); only the
   content inside `#page` needs to change.

The server tells these apart with a request header and renders
accordingly. That's the entire trick — everything else in this
template exists to produce and consume that header correctly.

```python
# app.py
def render_page(template, active_nav, **context):
    context.update(nav=NAV, active=active_nav)
    if request.headers.get("X-Requested-With") == "fetch":
        return render_template(template, **context)      # fragment only
    return render_template("shell.html", inner_template=template, **context)  # full page
```

- `shell.html` is the outer document: `<html>`, the stylesheet, the
  `<div id="page">` mount point, and `{% include inner_template %}`
  to drop the requested page's markup inside it on a hard load.
- Every page template (`templates/pages/*.html`) is written as a
  **fragment** — no `<html>`/`<head>`/`<body>` — so it can be rendered
  standalone (for a fetch) or included inside the shell (for a hard
  load) with zero duplication.

`static/app.js` sets `X-Requested-With: fetch` on every request it
makes, so the server always knows which of the two to send.

## `app.js`: the four things it does

The whole file is one closure with four `addEventListener` calls.
There's no client-side router, no virtual DOM, no state — every
response is a ready-to-insert HTML string, and the browser's own
`innerHTML`/`outerHTML` assignment is the "renderer."

### 1. Declarative triggers via `data-*` attributes

Instead of writing a `fetch` call per interactive element, elements
declare *what* to do and the script figures out *how*:

```html
<a href="/completed"
   data-get="/completed"
   data-target="#page"
   data-swap="innerHTML"
   data-push="true">Completed</a>
```

| Attribute | Meaning |
|---|---|
| `data-get` / `data-post` / `data-delete` | URL + HTTP method to call |
| `data-target` | CSS selector for the element to update (default `#page`) |
| `data-swap` | `innerHTML` (replace contents) or `outerHTML` (replace the element itself) |
| `data-push` | `"true"` to push the URL into browser history |
| `data-confirm` | Text for a `window.confirm()` gate before the request fires |

This mirrors the subset of HTMX's `hx-get`/`hx-target`/`hx-swap`/
`hx-push-url`/`hx-confirm` this app actually uses — see
[static/app.js](static/app.js) and the earlier HTMX→vanilla-JS
migration for the mapping.

### 2. Event delegation, not per-element binding

```js
document.addEventListener("click", function (e) {
  var el = e.target.closest("a[data-get], button[data-post], button[data-delete]");
  ...
});
```

All four listeners (`click`, `change`, `submit`, `popstate`) are bound
**once**, on `document`/`window`, at load time. This is the detail
that makes the "SPA feel" actually work with server-rendered fragments:
when a swap replaces `#task-list` with brand-new `<li>` elements, those
new elements are *never individually wired up* — they're just matched
by the next click because the listener lives on `document` and asks
"does the clicked thing match this selector?" at click time. No
framework, no re-binding step, no memory leaks from orphaned listeners.

> **Watch the selector scope.** `click`'s selector is deliberately
> `a[data-get], button[data-post], button[data-delete]` — not the
> more obvious `[data-get], [data-post], [data-delete]`. A generic
> attribute selector combined with `closest()` climbs *ancestors*, so
> clicking a plain `<button type="submit">` inside a
> `<form data-post="...">` would also match the form itself and fire
> a second, bodyless request racing the real form submission. This
> was an actual bug caught by testing — keep the tag scoping if you
> add new triggers.

### 3. One `request()` / `swap()` pair does all the I/O

```js
function request(method, url, body) {
  var headers = Object.assign({}, AJAX_HEADERS);
  if (body && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  }
  return fetch(url, { method: method, headers: headers, body: body })
    .then(function (res) { return res.text(); });
}

function swap(target, html, mode) {
  target[mode === "outerHTML" ? "outerHTML" : "innerHTML"] = html;
}
```

Every trigger — nav link, checkbox, delete button, form submit —
funnels through these two functions. The server always responds with
an HTML fragment (never JSON), so the client never parses or
re-serializes data; it just drops the string into the DOM. This keeps
all business logic (filtering active vs. completed tasks, computing
stats) on the Python side, in one place.

### 4. History via `pushState` + `popstate`

```js
if (push) history.pushState({ url: url }, "", url);
...
window.addEventListener("popstate", function () {
  request("GET", location.pathname, null).then(function (html) {
    swap(document.querySelector("#page"), html, "innerHTML");
  });
});
```

Nav clicks push a new URL without a real navigation. Back/forward
doesn't restore cached DOM (there's no cache) — it just re-issues a
fetch for `location.pathname` and swaps `#page` again. Simple, and
correct as long as every page's content is cheap to regenerate, which
it is here since it's all server-rendered from in-memory data.

## Building your own page on this template

Say you want a new `/settings` tab.

1. **Add the route** in `app.py`, following the existing pattern:
   ```python
   NAV.append({"key": "settings", "label": "Settings", "url": "/settings"})

   @app.route("/settings")
   def settings_view():
       return render_page("pages/settings.html", "settings", ...)
   ```
   `render_page` handles the fragment-vs-shell decision for you — you
   never branch on the request type yourself.

2. **Write the template** as a fragment, same shape as the others:
   ```html
   {% include "partials/_nav.html" %}
   <section class="page-body">
     <h2>Settings</h2>
     ...
   </section>
   ```
   Including `_nav.html` at the top of every page is what makes the
   active-tab highlighting update on every swap — it's plain
   server-rendered Jinja (`{{ 'active' if active == item.key else '' }}`),
   not something `app.js` manages.

3. **Wire up any interactive element** with `data-*` attributes instead
   of a custom `<script>` block:
   ```html
   <button data-post="/settings/reset" data-target="#page" data-confirm="Reset all settings?">
     Reset
   </button>
   ```
   As long as the endpoint returns an HTML fragment matching
   `data-target`, no JS changes are needed — `app.js` already knows
   how to handle it.

4. **Returning a partial fragment for an action** (like the existing
   `/tasks/<id>/toggle` endpoint): render just the sub-fragment
   (`partials/_task_list.html`-style) rather than the whole page, and
   point `data-target`/`data-swap` at the specific element being
   replaced. Keeps swaps small and avoids re-rendering unrelated UI.

### When you outgrow this pattern

This works well while every piece of state can be recomputed from a
fresh server render. If you eventually need optimistic UI updates,
partial client-side state, or complex cross-component reactivity, that's
a signal to reach for a proper framework (or HTMX, which offers more of
these primitives — see `data-*` table above for the direct mapping)
rather than growing `app.js`'s hand-rolled event delegation further.
