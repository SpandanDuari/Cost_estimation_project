from datetime import datetime
import io
import math
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

COCOMO_I_COEFFICIENTS = {
    "organic": {"a": 2.4, "b": 1.05},
    "semi-detached": {"a": 3.0, "b": 1.12},
    "embedded": {"a": 3.6, "b": 1.20},
}
COCOMO_II_A = 2.94
COCOMO_II_B = 0.91
MAX_INPUT_VALUE = 1_000_000_000


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
            model TEXT NOT NULL DEFAULT 'COCOMO_I',
            loc REAL,
            cost_per_dev REAL,
            cocomo_mode TEXT,
            eaf REAL,
            scale_factors_sum REAL,
            productivity REAL,
            avg_team_size REAL,
            effort REAL NOT NULL,
            time REAL NOT NULL,
            cost REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    report_columns = [row["name"] for row in cursor.execute("PRAGMA table_info(reports)").fetchall()]
    report_column_migrations = [
        ("model", "TEXT NOT NULL DEFAULT 'COCOMO_I'"),
        ("loc", "REAL"),
        ("cost_per_dev", "REAL"),
        ("cocomo_mode", "TEXT"),
        ("eaf", "REAL"),
        ("scale_factors_sum", "REAL"),
        ("productivity", "REAL"),
        ("avg_team_size", "REAL"),
    ]
    for column_name, column_definition in report_column_migrations:
        if column_name not in report_columns:
            cursor.execute(f"ALTER TABLE reports ADD COLUMN {column_name} {column_definition}")

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
         SELECT id, user_id, created_at, model, loc, cost_per_dev, cocomo_mode,
             eaf, scale_factors_sum, productivity, avg_team_size, effort, time, cost
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
         SELECT id, user_id, created_at, model, loc, cost_per_dev, cocomo_mode,
             eaf, scale_factors_sum, productivity, avg_team_size, effort, time, cost
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
         SELECT r.id, r.user_id, r.created_at, r.model, r.loc, r.cost_per_dev, r.cocomo_mode,
             r.eaf, r.scale_factors_sum, r.productivity, r.avg_team_size,
             r.effort, r.time, r.cost, u.username
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
         SELECT r.id, r.user_id, r.created_at, r.model, r.loc, r.cost_per_dev, r.cocomo_mode,
             r.eaf, r.scale_factors_sum, r.productivity, r.avg_team_size,
             r.effort, r.time, r.cost, u.username
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


def parse_positive_number(field_name, raw_value, min_value=0, max_value=MAX_INPUT_VALUE):
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid number.")

    if value <= min_value:
        raise ValueError(f"{field_name} must be greater than {min_value}.")
    if value > max_value:
        raise ValueError(f"{field_name} must be less than or equal to {max_value}.")
    return value


def parse_bounded_number(field_name, raw_value, min_value, max_value):
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid number.")

    if value < min_value or value > max_value:
        raise ValueError(f"{field_name} must be between {min_value} and {max_value}.")
    return value


def estimate_with_cocomo_i(loc, cost_per_dev, cocomo_mode):
    coefficients = COCOMO_I_COEFFICIENTS.get(cocomo_mode)
    if not coefficients:
        raise ValueError("Invalid COCOMO I mode selected.")

    kloc = loc / 1000
    effort = coefficients["a"] * (kloc ** coefficients["b"])
    development_time = 2.5 * (effort ** 0.38)
    total_cost = effort * cost_per_dev
    avg_team_size = effort / development_time if development_time > 0 else 0
    productivity = loc / effort if effort > 0 else 0

    return {
        "effort": effort,
        "time": development_time,
        "cost": total_cost,
        "avg_team_size": avg_team_size,
        "productivity": productivity,
        "cocomo_mode": cocomo_mode,
        "eaf": None,
        "scale_factors_sum": None,
    }


def estimate_with_cocomo_ii(loc, cost_per_dev, eaf, scale_factors):
    sf_sum = sum(scale_factors.values())
    exponent = COCOMO_II_B + 0.01 * sf_sum
    kloc = loc / 1000

    effort = COCOMO_II_A * eaf * (kloc ** exponent)
    development_time = 3.67 * (effort ** (0.28 + 0.2 * (exponent - COCOMO_II_B)))
    total_cost = effort * cost_per_dev
    avg_team_size = effort / development_time if development_time > 0 else 0
    productivity = loc / effort if effort > 0 else 0

    return {
        "effort": effort,
        "time": development_time,
        "cost": total_cost,
        "avg_team_size": avg_team_size,
        "productivity": productivity,
        "cocomo_mode": None,
        "eaf": eaf,
        "scale_factors_sum": sf_sum,
    }


def build_ai_feature_vector(loc, cost_per_dev, model, eaf, scale_factors_sum):
    return {
        "loc": loc,
        "cost_per_dev": cost_per_dev,
        "model_indicator": 1.0 if model == "COCOMO_II" else 0.0,
        "eaf": eaf,
        "scale_factors_sum": scale_factors_sum,
    }


def calculate_ai_distance(source, target):
    # Weighted normalized distance so LOC does not dominate all features
    weights = {
        "loc": 0.40,
        "cost_per_dev": 0.25,
        "model_indicator": 0.10,
        "eaf": 0.10,
        "scale_factors_sum": 0.15,
    }
    norms = {
        "loc": max(source["loc"], target["loc"], 1.0),
        "cost_per_dev": max(source["cost_per_dev"], target["cost_per_dev"], 1.0),
        "model_indicator": 1.0,
        "eaf": 10.0,
        "scale_factors_sum": 30.0,
    }

    squared = 0.0
    for key in weights:
        delta = (source[key] - target[key]) / norms[key]
        squared += weights[key] * (delta ** 2)
    return math.sqrt(squared)


def ai_predict_from_history(training_reports, input_vector):
    enriched = []
    for report in training_reports:
        if report.get("loc") is None or report.get("cost_per_dev") is None:
            continue

        report_model = report.get("model") or "COCOMO_I"
        report_vector = build_ai_feature_vector(
            loc=float(report.get("loc") or 0),
            cost_per_dev=float(report.get("cost_per_dev") or 0),
            model=report_model,
            eaf=float(report.get("eaf") or 1.0),
            scale_factors_sum=float(report.get("scale_factors_sum") or 15.0),
        )

        distance = calculate_ai_distance(input_vector, report_vector)
        enriched.append({
            "distance": distance,
            "effort": float(report.get("effort") or 0),
            "time": float(report.get("time") or 0),
            "cost": float(report.get("cost") or 0),
        })

    if not enriched:
        return None

    enriched.sort(key=lambda item: item["distance"])
    neighbors = enriched[: min(5, len(enriched))]

    weighted_effort = 0.0
    weighted_time = 0.0
    weighted_cost = 0.0
    total_weight = 0.0
    epsilon = 1e-6

    for item in neighbors:
        weight = 1.0 / (item["distance"] + epsilon)
        weighted_effort += item["effort"] * weight
        weighted_time += item["time"] * weight
        weighted_cost += item["cost"] * weight
        total_weight += weight

    if total_weight <= 0:
        return None

    avg_distance = sum(item["distance"] for item in neighbors) / len(neighbors)
    confidence = max(35.0, min(99.0, 100.0 - (avg_distance * 100.0)))

    return {
        "effort": weighted_effort / total_weight,
        "time": weighted_time / total_weight,
        "cost": weighted_cost / total_weight,
        "confidence": confidence,
        "neighbors_used": len(neighbors),
    }


def predict_with_ai_or_fallback(training_reports, loc, cost_per_dev, model, eaf=None, scale_factors_sum=None):
    input_vector = build_ai_feature_vector(
        loc=loc,
        cost_per_dev=cost_per_dev,
        model=model,
        eaf=eaf if eaf is not None else 1.0,
        scale_factors_sum=scale_factors_sum if scale_factors_sum is not None else 15.0,
    )

    ai_estimate = ai_predict_from_history(training_reports, input_vector)
    if ai_estimate and len(training_reports) >= 3:
        ai_estimate["source"] = "history-trained kNN"
        return ai_estimate

    # Fallback baseline when history is not enough for meaningful training
    if model == "COCOMO_I":
        fallback = estimate_with_cocomo_i(loc, cost_per_dev, "organic")
    else:
        sf_each = (scale_factors_sum if scale_factors_sum is not None else 15.0) / 5.0
        fallback = estimate_with_cocomo_ii(
            loc,
            cost_per_dev,
            eaf if eaf is not None else 1.0,
            {
                "prec": sf_each,
                "flex": sf_each,
                "resl": sf_each,
                "team": sf_each,
                "pmat": sf_each,
            },
        )

    return {
        "effort": fallback["effort"],
        "time": fallback["time"],
        "cost": fallback["cost"],
        "confidence": 55.0,
        "neighbors_used": len(training_reports),
        "source": "fallback-model",
    }

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
    ai_result = None
    ai_error = None

    if request.method == "POST":
        try:
            action = request.form.get("action", "estimate")

            if action == "ai_predict":
                ai_loc = parse_positive_number("AI Project size (LOC)", request.form.get("ai_loc"))
                ai_cost_per_dev = parse_positive_number("AI Cost per developer", request.form.get("ai_cost"))
                ai_model = request.form.get("ai_model", "COCOMO_I").strip().upper()

                ai_eaf = None
                ai_scale_factors_sum = None
                if ai_model == "COCOMO_II":
                    ai_eaf = parse_positive_number("AI EAF", request.form.get("ai_eaf"), min_value=0, max_value=10)
                    ai_scale_factors_sum = parse_bounded_number("AI Scale Factors Sum", request.form.get("ai_sf_sum"), 0, 30)
                elif ai_model != "COCOMO_I":
                    raise ValueError("Please select a valid AI model.")

                training_reports = get_all_reports() if is_admin else get_reports_for_user(user_id)
                predicted = predict_with_ai_or_fallback(
                    training_reports,
                    loc=ai_loc,
                    cost_per_dev=ai_cost_per_dev,
                    model=ai_model,
                    eaf=ai_eaf,
                    scale_factors_sum=ai_scale_factors_sum,
                )

                ai_result = {
                    "model": ai_model,
                    "loc": round(ai_loc, 2),
                    "cost_per_dev": round(ai_cost_per_dev, 2),
                    "eaf": round(ai_eaf, 3) if ai_eaf is not None else None,
                    "scale_factors_sum": round(ai_scale_factors_sum, 3) if ai_scale_factors_sum is not None else None,
                    "effort": round(predicted["effort"], 2),
                    "time": round(predicted["time"], 2),
                    "cost": round(predicted["cost"], 2),
                    "confidence": round(predicted["confidence"], 1),
                    "neighbors_used": predicted["neighbors_used"],
                    "source": predicted["source"],
                }

            elif action == "estimate":
                loc = parse_positive_number("Project size (LOC)", request.form.get("loc"))
                cost_per_dev = parse_positive_number("Cost per developer", request.form.get("cost"))
                model = request.form.get("model", "COCOMO_I").strip().upper()

                estimate_data = None
                if model == "COCOMO_I":
                    cocomo_mode = request.form.get("cocomo_mode", "organic").strip().lower()
                    estimate_data = estimate_with_cocomo_i(loc, cost_per_dev, cocomo_mode)
                elif model == "COCOMO_II":
                    eaf = parse_positive_number("Effort Adjustment Factor (EAF)", request.form.get("eaf"), min_value=0, max_value=10)
                    scale_factors = {
                        "prec": parse_bounded_number("PREC", request.form.get("prec"), 0, 6),
                        "flex": parse_bounded_number("FLEX", request.form.get("flex"), 0, 6),
                        "resl": parse_bounded_number("RESL", request.form.get("resl"), 0, 6),
                        "team": parse_bounded_number("TEAM", request.form.get("team"), 0, 6),
                        "pmat": parse_bounded_number("PMAT", request.form.get("pmat"), 0, 6),
                    }
                    estimate_data = estimate_with_cocomo_ii(loc, cost_per_dev, eaf, scale_factors)
                else:
                    raise ValueError("Please select a valid estimation model.")

                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn = get_db_connection()
                cursor = conn.execute(
                    """
                    INSERT INTO reports (
                        user_id, created_at, model, loc, cost_per_dev, cocomo_mode,
                        eaf, scale_factors_sum, productivity, avg_team_size, effort, time, cost
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        created_at,
                        model,
                        round(loc, 2),
                        round(cost_per_dev, 2),
                        estimate_data["cocomo_mode"],
                        round(estimate_data["eaf"], 3) if estimate_data["eaf"] is not None else None,
                        round(estimate_data["scale_factors_sum"], 3) if estimate_data["scale_factors_sum"] is not None else None,
                        round(estimate_data["productivity"], 2),
                        round(estimate_data["avg_team_size"], 2),
                        round(estimate_data["effort"], 2),
                        round(estimate_data["time"], 2),
                        round(estimate_data["cost"], 2),
                    )
                )
                conn.commit()
                report_id = cursor.lastrowid
                conn.close()

                result = {
                    "id": report_id,
                    "created_at": created_at,
                    "model": model,
                    "loc": round(loc, 2),
                    "cost_per_dev": round(cost_per_dev, 2),
                    "cocomo_mode": estimate_data["cocomo_mode"],
                    "eaf": round(estimate_data["eaf"], 3) if estimate_data["eaf"] is not None else None,
                    "scale_factors_sum": round(estimate_data["scale_factors_sum"], 3) if estimate_data["scale_factors_sum"] is not None else None,
                    "effort": round(estimate_data["effort"], 2),
                    "time": round(estimate_data["time"], 2),
                    "cost": round(estimate_data["cost"], 2),
                    "avg_team_size": round(estimate_data["avg_team_size"], 2),
                    "productivity": round(estimate_data["productivity"], 2),
                }
            else:
                raise ValueError("Invalid action requested.")

        except ValueError as exc:
            if request.form.get("action") == "ai_predict":
                ai_error = str(exc)
            else:
                error = str(exc)

    report_history = get_all_reports() if is_admin else get_reports_for_user(user_id)
    users_list = get_all_users() if is_admin else []

    return render_template(
        "index.html",
        result=result,
        error=error,
        ai_result=ai_result,
        ai_error=ai_error,
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
        f"Model: {report.get('model') or 'COCOMO_I'}\n"
        f"Project Size (LOC): {report.get('loc') if report.get('loc') is not None else 'N/A'}\n"
        f"Cost per Developer: {report.get('cost_per_dev') if report.get('cost_per_dev') is not None else 'N/A'}\n"
        f"COCOMO I Mode: {report.get('cocomo_mode') if report.get('cocomo_mode') else 'N/A'}\n"
        f"EAF: {report.get('eaf') if report.get('eaf') is not None else 'N/A'}\n"
        f"Scale Factors Sum: {report.get('scale_factors_sum') if report.get('scale_factors_sum') is not None else 'N/A'}\n"
        f"Effort: {report['effort']} Person/Months\n"
        f"Development Time: {report['time']} Months\n"
        f"Average Team Size: {report.get('avg_team_size') if report.get('avg_team_size') is not None else 'N/A'}\n"
        f"Productivity: {report.get('productivity') if report.get('productivity') is not None else 'N/A'} LOC per Person-Month\n"
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
        f"Model: {report.get('model') or 'COCOMO_I'}",
        f"Project Size (LOC): {report.get('loc') if report.get('loc') is not None else 'N/A'}",
        f"Cost per Developer: {report.get('cost_per_dev') if report.get('cost_per_dev') is not None else 'N/A'}",
        f"COCOMO I Mode: {report.get('cocomo_mode') if report.get('cocomo_mode') else 'N/A'}",
        f"EAF: {report.get('eaf') if report.get('eaf') is not None else 'N/A'}",
        f"Scale Factors Sum: {report.get('scale_factors_sum') if report.get('scale_factors_sum') is not None else 'N/A'}",
        f"Effort: {report['effort']} Person/Months",
        f"Development Time: {report['time']} Months",
        f"Average Team Size: {report.get('avg_team_size') if report.get('avg_team_size') is not None else 'N/A'}",
        f"Productivity: {report.get('productivity') if report.get('productivity') is not None else 'N/A'} LOC/PM",
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