(function () {
  var AJAX_HEADERS = { "X-Requested-With": "fetch" };

  function swap(target, html, mode) {
    if (mode === "outerHTML") {
      target.outerHTML = html;
    } else {
      target.innerHTML = html;
    }
  }

  function request(method, url, body) {
    var headers = Object.assign({}, AJAX_HEADERS);
    if (body && !(body instanceof FormData)) {
      headers["Content-Type"] = "application/x-www-form-urlencoded";
    }
    return fetch(url, { method: method, headers: headers, body: body }).then(function (res) {
      return res.text();
    });
  }

  function swapFromEl(el, method, url) {
    var targetSel = el.dataset.target || "#page";
    var swapMode = el.dataset.swap || "innerHTML";
    var push = el.dataset.push === "true";
    var target = document.querySelector(targetSel);
    if (!target) return;

    request(method, url, null).then(function (html) {
      swap(target, html, swapMode);
      if (push) {
        history.pushState({ url: url }, "", url);
      }
    });
  }

  // Clicks on links/buttons carrying data-get / data-post / data-delete
  // (scoped to a/button so a click inside a data-post <form> doesn't
  // also match the form itself via closest())
  document.addEventListener("click", function (e) {
    var el = e.target.closest("a[data-get], button[data-post], button[data-delete]");
    if (!el) return;

    var confirmMsg = el.dataset.confirm;
    if (confirmMsg && !window.confirm(confirmMsg)) return;

    e.preventDefault();
    if (el.dataset.get) swapFromEl(el, "GET", el.dataset.get);
    else if (el.dataset.post) swapFromEl(el, "POST", el.dataset.post);
    else if (el.dataset.delete) swapFromEl(el, "DELETE", el.dataset.delete);
  });

  // Checkbox toggles (data-post on an <input type="checkbox">)
  document.addEventListener("change", function (e) {
    var el = e.target.closest("input[type=checkbox][data-post]");
    if (!el) return;
    swapFromEl(el, "POST", el.dataset.post);
  });

  // Forms carrying data-post
  document.addEventListener("submit", function (e) {
    var form = e.target.closest("form[data-post]");
    if (!form) return;
    e.preventDefault();

    var targetSel = form.dataset.target || "#page";
    var swapMode = form.dataset.swap || "innerHTML";
    var target = document.querySelector(targetSel);
    if (!target) return;

    request("POST", form.dataset.post, new FormData(form)).then(function (html) {
      swap(target, html, swapMode);
      form.reset();
    });
  });

  // Browser back/forward: re-fetch the page fragment for the current URL
  window.addEventListener("popstate", function () {
    var target = document.querySelector("#page");
    request("GET", location.pathname, null).then(function (html) {
      swap(target, html, "innerHTML");
    });
  });
})();
