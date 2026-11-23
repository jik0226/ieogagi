# Test cases for security/semgrep/injection.yml.
# Annotations: the line after a ruleid comment must be reported; after an ok comment it must stay silent.
import ast
import os
import subprocess

from fastapi.responses import RedirectResponse
from sqlalchemy import text

conn = cursor = session = User = select = None


def cases(user_code, name, target):
    """Parameters are used on purpose: Semgrep constant propagation would turn literals into matches."""
    # ruleid: ieogagi-no-eval-exec
    eval(user_code)
    # ruleid: ieogagi-no-eval-exec
    exec(user_code)
    # ruleid: ieogagi-no-eval-exec
    __import__(name)
    # ruleid: ieogagi-no-eval-exec
    compile(user_code, "<string>", "exec")
    # ruleid: ieogagi-no-eval-exec
    compile(user_code, "<string>", mode="exec")
    # ruleid: ieogagi-no-eval-exec
    eval(f"{name} + 1")
    # ok: ieogagi-no-eval-exec
    eval("1 + 1")
    # ok: ieogagi-no-eval-exec
    ast.literal_eval(user_code)
    # ok: ieogagi-no-eval-exec
    __import__("json")

    # ruleid: ieogagi-no-raw-sql-format
    text(f"SELECT * FROM users WHERE id = {name}")
    # ruleid: ieogagi-no-raw-sql-format
    text("SELECT * FROM users WHERE id = %s" % name)
    # ruleid: ieogagi-no-raw-sql-format
    text("SELECT * FROM users WHERE id = {}".format(name))
    # ruleid: ieogagi-no-raw-sql-format
    text("SELECT * FROM users WHERE id = " + name)
    # ruleid: ieogagi-no-raw-sql-format
    conn.execute(f"DELETE FROM users WHERE id = {name}")
    # ruleid: ieogagi-no-raw-sql-format
    cursor.execute("DELETE FROM users WHERE id = %s" % name)
    # ruleid: ieogagi-no-raw-sql-format
    session.execute(text(f"SELECT {name}"))
    # ok: ieogagi-no-raw-sql-format
    text("SELECT * FROM users WHERE id = :id")
    # ok: ieogagi-no-raw-sql-format
    session.execute(text("SELECT * FROM users WHERE id = :id"), {"id": name})
    # ok: ieogagi-no-raw-sql-format
    cursor.execute("SELECT * FROM users WHERE id = %s", (name,))
    # ok: ieogagi-no-raw-sql-format
    text("SELECT 1 " + "FROM dual")

    # ruleid: ieogagi-no-raw-sql-format
    text(" AND ".join(name))
    # ruleid: ieogagi-no-raw-sql-format
    conn.execute("SELECT * FROM users WHERE " + " AND ".join(name))
    # ok: ieogagi-no-raw-sql-format
    session.execute(text("SELECT * FROM users WHERE id = :id").bindparams(id=name))
    # ok: ieogagi-no-raw-sql-format
    session.execute(select(User).where(User.name == "prefix-" + name))

    # ruleid: ieogagi-no-shell
    subprocess.run(["ls"], shell=True)
    # ruleid: ieogagi-no-shell
    subprocess.Popen("ls", shell=True)
    # ruleid: ieogagi-no-shell
    os.system("ls")
    # ruleid: ieogagi-no-shell
    os.popen("ls")
    # ruleid: ieogagi-no-shell
    subprocess.getoutput("ls")
    # ok: ieogagi-no-shell
    subprocess.run(["ls", "-l"], check=True)
    # ok: ieogagi-no-shell
    subprocess.run(["ls"], shell=False, check=True)

    # ruleid: ieogagi-no-ssrf-redirect
    RedirectResponse(target)
    # ruleid: ieogagi-no-ssrf-redirect
    RedirectResponse(url=target)
    # ruleid: ieogagi-no-ssrf-redirect
    RedirectResponse(f"/next?to={target}", status_code=303)
    # ok: ieogagi-no-ssrf-redirect
    RedirectResponse("/login")
    # ok: ieogagi-no-ssrf-redirect
    RedirectResponse(url="/login", status_code=303)


def sql_built_in_variable(name, parts, flag):
    """SQL assembled in a variable first and passed to text()/execute() afterwards."""
    query = f"SELECT * FROM users WHERE id = {name}"
    # ruleid: ieogagi-no-raw-sql-format
    text(query)

    percent_query = "SELECT * FROM users WHERE id = %s" % name
    # ruleid: ieogagi-no-raw-sql-format
    conn.execute(percent_query)

    format_query = "SELECT * FROM users WHERE id = {}".format(name)
    # ruleid: ieogagi-no-raw-sql-format
    session.execute(text(format_query))

    plus_query = "SELECT * FROM users WHERE id = " + name
    # ruleid: ieogagi-no-raw-sql-format
    cursor.execute(plus_query)

    joined_query = " AND ".join(parts)
    # ruleid: ieogagi-no-raw-sql-format
    text(joined_query)

    appended_query = "SELECT * FROM users WHERE "
    appended_query += f"id = {name}"
    # ruleid: ieogagi-no-raw-sql-format
    text(appended_query)

    if flag:
        branch_query = f"SELECT * FROM users WHERE id = {name}"
    else:
        branch_query = "SELECT * FROM users"
    # ruleid: ieogagi-no-raw-sql-format
    text(branch_query)

    base_query = f"SELECT * FROM users WHERE id = {name}"
    limited_query = base_query + " LIMIT 1"
    # ruleid: ieogagi-no-raw-sql-format
    conn.exec_driver_sql(limited_query)

    literal_query = "SELECT * FROM users WHERE id = :id"
    # ok: ieogagi-no-raw-sql-format
    text(literal_query)
    # ok: ieogagi-no-raw-sql-format
    session.execute(text(literal_query), {"id": name})
    constant_query = "SELECT * FROM " + "users"
    # ok: ieogagi-no-raw-sql-format
    text(constant_query)
    bound_query = text("SELECT * FROM users WHERE id = :id")
    # ok: ieogagi-no-raw-sql-format
    session.execute(bound_query.bindparams(id=name), {"unused": f"{name}"})
    # ok: ieogagi-no-raw-sql-format
    cursor.execute("SELECT * FROM users WHERE id = %s", (f"{name}",))
