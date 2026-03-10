from datetime import datetime
import io
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, Response, flash
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "cost-estimation-secret-key"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "cost_estimation.db")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    user_columns = [row["name"] for row in cursor.execute("PRAGMA table_info(users)").fetchall()]
    if "is_admin" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            effort REAL NOT NULL,
            time REAL NOT NULL,
            cost REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    conn.commit()
    conn.close()


def ensure_admin_user():
    conn = get_db_connection()
    admin = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (ADMIN_USERNAME,)
    ).fetchone()

    if admin:
        conn.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (ADMIN_USERNAME,))
    else:
        conn.execute(
            """
            INSERT INTO users (username, password_hash, is_admin, created_at)
            VALUES (?, ?, 1, ?)
            """,
            (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )

    conn.commit()
    conn.close()


init_db()
ensure_admin_user()


def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT id, username, password_hash, is_admin FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()
    return user


def get_all_users():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, username, is_admin, created_at FROM users ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_reports_for_user(user_id):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT id, user_id, created_at, effort, time, cost
        FROM reports
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_report_for_user(user_id, report_id):
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT id, user_id, created_at, effort, time, cost
        FROM reports
        WHERE user_id = ? AND id = ?
        """,
        (user_id, report_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_report_for_user(user_id, report_id):
    conn = get_db_connection()
    cursor = conn.execute(
        "DELETE FROM reports WHERE user_id = ? AND id = ?",
        (user_id, report_id)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def delete_report_by_id(report_id):
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_report_by_id(report_id):
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT r.id, r.user_id, r.created_at, r.effort, r.time, r.cost, u.username
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.id = ?
        """,
        (report_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_reports():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT r.id, r.user_id, r.created_at, r.effort, r.time, r.cost, u.username
        FROM reports r
        JOIN users u ON r.user_id = u.id
        ORDER BY r.id DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_user_account(user_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM reports WHERE user_id = ?", (user_id,))
    deleted_user = conn.execute("DELETE FROM users WHERE id = ?", (user_id,)).rowcount > 0
    conn.commit()
    conn.close()
    return deleted_user

@app.route("/")
def home():
    if session.get("user"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("auth"))


@app.route("/auth", methods=["GET", "POST"])
def auth():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            error = "Username and password are required."
        else:
            user_record = get_user_by_username(username)
            if user_record and check_password_hash(user_record["password_hash"], password):
                session["user"] = username
                return redirect(url_for("dashboard"))
            error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    message = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            error = "Username and password are required."
        elif get_user_by_username(username):
            error = "Username already exists. Please choose another one."
        else:
            password_hash = generate_password_hash(password)
            conn = get_db_connection()
            conn.execute(
                """
                INSERT INTO users (username, password_hash, is_admin, created_at)
                VALUES (?, ?, 0, ?)
                """,
                (username, password_hash, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            conn.close()
            message = "Account created successfully. Please log in."

    return render_template("signup.html", error=error, message=message)


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("user"):
        return redirect(url_for("auth"))

    username = session.get("user")
    user_record = get_user_by_username(username)

    if not user_record:
        session.clear()
        return redirect(url_for("auth"))

    user_id = user_record["id"]
    is_admin = bool(user_record["is_admin"])

    result = None
    error = None

    if request.method == "POST":
        try:
            loc = float(request.form["loc"])
            cost_per_dev = float(request.form["cost"])

            # Validation (NFR-01 Accuracy + NFR-04 Scalability)
            if loc <= 0 or cost_per_dev <= 0:
                error = "Please enter valid positive numbers."
            else:
                kloc = loc / 1000  # Convert LOC to KLOC

                # Basic COCOMO (Organic Mode)
                a = 2.4
                b = 1.05

                effort = a * (kloc ** b)         # FR-04, FR-05
                time = 2.5 * (effort ** 0.38)   # FR-06, FR-07
                total_cost = effort * cost_per_dev  # FR-02, FR-03

                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn = get_db_connection()
                cursor = conn.execute(
                    """
                    INSERT INTO reports (user_id, created_at, effort, time, cost)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, created_at, round(effort, 2), round(time, 2), round(total_cost, 2))
                )
                conn.commit()
                report_id = cursor.lastrowid
                conn.close()

                result = {
                    "id": report_id,
                    "created_at": created_at,
                    "effort": round(effort, 2),
                    "time": round(time, 2),
                    "cost": round(total_cost, 2)
                }

        except ValueError:
            error = "Invalid input. Please enter numeric values only."

    report_history = get_all_reports() if is_admin else get_reports_for_user(user_id)
    users_list = get_all_users() if is_admin else []

    return render_template(
        "index.html",
        result=result,
        error=error,
        user=username,
        report_history=report_history,
        is_admin=is_admin,
        users_list=users_list
    )


@app.route("/download")
def download_page():
    if not session.get("user"):
        return redirect(url_for("auth"))

    username = session.get("user")
    user_record = get_user_by_username(username)

    if not user_record:
        session.clear()
        return redirect(url_for("auth"))

    is_admin = bool(user_record["is_admin"])
    reports = get_all_reports() if is_admin else get_reports_for_user(user_record["id"])
    return render_template("download.html", reports=reports, user=username, is_admin=is_admin)


@app.route("/report/<int:report_id>")
def report_detail(report_id):
    if not session.get("user"):
        return redirect(url_for("auth"))

    username = session.get("user")
    user_record = get_user_by_username(username)

    if not user_record:
        session.clear()
        return redirect(url_for("auth"))

    report = get_report_by_id(report_id)
    if not report:
        flash("Report not found.", "error")
        return redirect(url_for("dashboard"))

    is_admin = bool(user_record["is_admin"])
    is_owner = report["user_id"] == user_record["id"]
    if not is_admin and not is_owner:
        flash("You are not authorized to view this report.", "error")
        return redirect(url_for("dashboard"))

    return render_template(
        "report_detail.html",
        report=report,
        user=username,
        is_admin=is_admin,
        is_owner=is_owner
    )


@app.route("/download-report")
@app.route("/download-report/<int:report_id>")
def download_report(report_id=None):
    if not session.get("user"):
        return redirect(url_for("auth"))

    username = session.get("user")
    user_record = get_user_by_username(username)

    if not user_record:
        return redirect(url_for("download_page"))

    user_id = user_record["id"]
    is_admin = bool(user_record["is_admin"])
    user_reports = get_reports_for_user(user_id)

    if not user_reports and not is_admin:
        return redirect(url_for("download_page"))

    if report_id is None:
        all_reports = get_all_reports() if is_admin else user_reports
        if not all_reports:
            return redirect(url_for("download_page"))
        report = all_reports[0]
    else:
        report = get_report_by_id(report_id) if is_admin else get_report_for_user(user_id, report_id)
        if report is None:
            return redirect(url_for("download_page"))

    report_text = (
        "Software Cost Estimation Report\n"
        "===============================\n"
        f"User: {username}\n"
        f"Report ID: {report['id']}\n"
        f"Generated On: {report['created_at']}\n"
        f"Effort: {report['effort']} Person/Months\n"
        f"Development Time: {report['time']} Months\n"
        f"Total Cost: ₹ {report['cost']}\n"
    )

    return Response(
        report_text,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment;filename=cost_estimation_report_{report['id']}.txt"}
    )


@app.route("/download-report-pdf/<int:report_id>")
def download_report_pdf(report_id):
    if not session.get("user"):
        return redirect(url_for("auth"))

    username = session.get("user")
    user_record = get_user_by_username(username)

    if not user_record:
        return redirect(url_for("download_page"))

    is_admin = bool(user_record["is_admin"])
    report = get_report_by_id(report_id) if is_admin else get_report_for_user(user_record["id"], report_id)
    if not report:
        return redirect(url_for("download_page"))

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 60

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Software Cost Estimation Report")
    y -= 30

    pdf.setFont("Helvetica", 12)
    lines = [
        f"User: {username}",
        f"Report ID: {report['id']}",
        f"Generated On: {report['created_at']}",
        f"Effort: {report['effort']} Person/Months",
        f"Development Time: {report['time']} Months",
        f"Total Cost: INR {report['cost']}"
    ]

    for line in lines:
        pdf.drawString(50, y, line)
        y -= 22

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=cost_estimation_report_{report['id']}.pdf"}
    )


@app.route("/delete-report/<int:report_id>", methods=["POST"])
def delete_report(report_id):
    if not session.get("user"):
        return redirect(url_for("auth"))

    username = session.get("user")
    user_record = get_user_by_username(username)

    if not user_record:
        session.clear()
        return redirect(url_for("auth"))

    is_admin = bool(user_record["is_admin"])
    deleted = delete_report_by_id(report_id) if is_admin else delete_report_for_user(user_record["id"], report_id)
    if deleted:
        flash("Report deleted successfully.", "success")
    else:
        flash("Report not found or already deleted.", "error")

    source = request.args.get("source", "dashboard")
    if source == "download":
        return redirect(url_for("download_page"))
    return redirect(url_for("dashboard"))


@app.route("/admin/delete-user/<int:user_id>", methods=["POST"])
def admin_delete_user(user_id):
    if not session.get("user"):
        return redirect(url_for("auth"))

    current_user = get_user_by_username(session.get("user"))
    if not current_user or not bool(current_user["is_admin"]):
        flash("Only admin can delete accounts.", "error")
        return redirect(url_for("dashboard"))

    target_conn = get_db_connection()
    target_user = target_conn.execute(
        "SELECT id, username, is_admin FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    target_conn.close()

    if not target_user:
        flash("User not found.", "error")
        return redirect(url_for("dashboard"))

    if target_user["id"] == current_user["id"]:
        flash("Admin account cannot delete itself.", "error")
        return redirect(url_for("dashboard"))

    if bool(target_user["is_admin"]):
        flash("Cannot delete another admin account.", "error")
        return redirect(url_for("dashboard"))

    deleted = delete_user_account(target_user["id"])
    if deleted:
        flash(f"User '{target_user['username']}' and all their reports were deleted.", "success")
    else:
        flash("Unable to delete user.", "error")

    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth"))

if __name__ == "__main__":
    app.run(debug=True)