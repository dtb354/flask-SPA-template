from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from itertools import count

app = Flask(__name__)

# In-memory "database" just for this example
tasks = [
    {"id": 1, "text": "Learn HTMX", "done": True, "created": "2026-09-15"},
    {"id": 2, "text": "Wire it up to Flask", "done": True, "created": "2026-09-16"},
    {"id": 3, "text": "Build a multi-page SPA feel", "done": False, "created": "2026-09-17"},
]
_ids = count(4)

NAV = [
    {"key": "tasks", "label": "Tasks", "url": "/tasks"},
    {"key": "completed", "label": "Completed", "url": "/completed"},
    {"key": "stats", "label": "Stats", "url": "/stats"},
    {"key": "about", "label": "About", "url": "/about"},
]


def render_page(template, active_nav, **context):
    """Render a page fragment (for HTMX swaps) or the full shell on a hard load."""
    context.update(nav=NAV, active=active_nav)
    if request.headers.get("X-Requested-With") == "fetch":
        return render_template(template, **context)
    return render_template("shell.html", inner_template=template, **context)


@app.route("/")
def index():
    return redirect(url_for("active_tasks_view"))


@app.route("/tasks")
def active_tasks_view():
    active = [t for t in tasks if not t["done"]]
    return render_page("pages/tasks.html", "tasks", tasks=active)


@app.route("/tasks", methods=["POST"])
def add_task():
    text = request.form.get("text", "").strip()
    if text:
        tasks.append({
            "id": next(_ids),
            "text": text,
            "done": False,
            "created": datetime.now().strftime("%Y-%m-%d"),
        })
    active = [t for t in tasks if not t["done"]]
    return render_template("partials/_task_list.html", tasks=active)


@app.route("/tasks/<int:task_id>/toggle", methods=["POST"])
def toggle_task(task_id):
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = not t["done"]
    if request.args.get("from") == "completed":
        done = [t for t in tasks if t["done"]]
        return render_template("partials/_completed_list.html", tasks=done)
    active = [t for t in tasks if not t["done"]]
    return render_template("partials/_task_list.html", tasks=active)


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    global tasks
    tasks = [t for t in tasks if t["id"] != task_id]
    if request.args.get("from") == "completed":
        done = [t for t in tasks if t["done"]]
        return render_template("partials/_completed_list.html", tasks=done)
    active = [t for t in tasks if not t["done"]]
    return render_template("partials/_task_list.html", tasks=active)


@app.route("/completed")
def completed_view():
    done = [t for t in tasks if t["done"]]
    return render_page("pages/completed.html", "completed", tasks=done)


@app.route("/completed/clear", methods=["POST"])
def clear_completed():
    global tasks
    tasks = [t for t in tasks if not t["done"]]
    return render_template("partials/_completed_list.html", tasks=[])


@app.route("/stats")
def stats_view():
    total = len(tasks)
    done = len([t for t in tasks if t["done"]])
    active = total - done
    pct = round((done / total) * 100) if total else 0
    return render_page(
        "pages/stats.html", "stats",
        total=total, done=done, active=active, pct=pct,
    )


@app.route("/about")
def about_view():
    return render_page("pages/about.html", "about")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
