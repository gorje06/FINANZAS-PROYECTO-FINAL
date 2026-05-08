import json
import os
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_conn, init_db
from finance import build_schedule


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "creditcar-dev-secret")
init_db()


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper


@app.get("/")
def root():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("Completa usuario y contraseña.")
            return render_template("register.html")

        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            conn.commit()
            flash("Cuenta creada. Ahora inicia sesión.")
            return redirect(url_for("login"))
        except Exception:
            flash("No se pudo registrar. Usuario ya existe.")
        finally:
            conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_conn()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Credenciales inválidas.")
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        try:
            nombres_cliente = request.form["nombres_cliente"].strip()
            apellidos_cliente = request.form["apellidos_cliente"].strip()
            dni_cliente = request.form["dni_cliente"].strip()
            correo_cliente = request.form.get("correo_cliente", "").strip()
            telefono_cliente = request.form.get("telefono_cliente", "").strip()
            direccion_cliente = request.form.get("direccion_cliente", "").strip()
            ingresos_mensuales = float(request.form["ingresos_mensuales"])
            marca_vehiculo = request.form["marca_vehiculo"].strip()
            modelo_vehiculo = request.form["modelo_vehiculo"].strip()
            precio_vehiculo = float(request.form["precio_vehiculo"])
            cuota_inicial_pct = float(request.form["cuota_inicial_pct"])
            moneda = request.form["moneda"]
            tipo_tasa = request.form["tipo_tasa"]
            tasa_interes = float(request.form["tasa_interes"]) / 100.0
            capitalizacion_raw = request.form.get("capitalizacion", "").strip()
            capitalizacion = int(capitalizacion_raw) if capitalizacion_raw else None
            plazo_meses = int(request.form["plazo_meses"])
            periodo_gracia = request.form["periodo_gracia"]
            meses_gracia = int(request.form.get("meses_gracia", 0))
            seguro_desgravamen = float(request.form["seguro_desgravamen"]) / 100.0
            seguro_vehicular = float(request.form["seguro_vehicular"]) / 100.0
            portes = float(request.form["portes"])

            result = build_schedule(
                precio_vehiculo=precio_vehiculo,
                cuota_inicial_pct=cuota_inicial_pct,
                tipo_tasa=tipo_tasa,
                tasa_interes=tasa_interes,
                plazo_meses=plazo_meses,
                periodo_gracia=periodo_gracia,
                meses_gracia=meses_gracia,
                seguro_desgravamen=seguro_desgravamen,
                seguro_vehicular=seguro_vehicular,
                portes=portes,
                capitalizacion=capitalizacion,
            )

            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO plans (
                    user_id, nombres_cliente, apellidos_cliente, dni_cliente, correo_cliente, telefono_cliente,
                    direccion_cliente, ingresos_mensuales, marca_vehiculo, modelo_vehiculo, precio_vehiculo,
                    cuota_inicial_pct, moneda, tipo_tasa, tasa_interes, capitalizacion, plazo_meses,
                    periodo_gracia, meses_gracia, seguro_desgravamen, seguro_vehicular, portes, tem, cuota_base,
                    van, tir, tcea, total_financiado, flujo_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    nombres_cliente,
                    apellidos_cliente,
                    dni_cliente,
                    correo_cliente,
                    telefono_cliente,
                    direccion_cliente,
                    ingresos_mensuales,
                    marca_vehiculo,
                    modelo_vehiculo,
                    precio_vehiculo,
                    cuota_inicial_pct,
                    moneda,
                    tipo_tasa,
                    tasa_interes,
                    capitalizacion,
                    plazo_meses,
                    periodo_gracia,
                    meses_gracia,
                    seguro_desgravamen,
                    seguro_vehicular,
                    portes,
                    result.tem,
                    result.cuota_base,
                    result.van,
                    result.tir,
                    result.tcea,
                    result.saldo_inicial,
                    json.dumps(result.flujo),
                ),
            )
            plan_id = cur.lastrowid

            for row in result.schedule:
                cur.execute(
                    """
                    INSERT INTO plan_schedule (plan_id, periodo, cuota_total, interes, amortizacion, saldo_final, seguro, portes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan_id,
                        row.periodo,
                        row.cuota_total,
                        row.interes,
                        row.amortizacion,
                        row.saldo_final,
                        row.seguro,
                        row.portes,
                    ),
                )

            conn.commit()
            conn.close()
            return redirect(url_for("plan_detail", plan_id=plan_id))
        except Exception as exc:
            flash(f"Error en cálculo o registro: {exc}")

    conn = get_conn()
    plans = conn.execute(
        "SELECT id, nombres_cliente, apellidos_cliente, marca_vehiculo, modelo_vehiculo, created_at FROM plans WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("dashboard.html", plans=plans, username=session.get("username", ""))


@app.get("/plans/<int:plan_id>")
@login_required
def plan_detail(plan_id: int):
    conn = get_conn()
    plan = conn.execute("SELECT * FROM plans WHERE id = ? AND user_id = ?", (plan_id, session["user_id"])).fetchone()
    schedule = conn.execute(
        "SELECT * FROM plan_schedule WHERE plan_id = ? ORDER BY periodo ASC", (plan_id,)
    ).fetchall()
    conn.close()
    if not plan:
        flash("Plan no encontrado.")
        return redirect(url_for("dashboard"))
    return render_template("plan_detail.html", plan=plan, schedule=schedule)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port)
