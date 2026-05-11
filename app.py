"""FinanCuota — simulador de crédito vehicular (método francés). Autor: gorje."""

import json
import os
import re
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_conn, init_db
from finance import build_schedule


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "financuota-dev-secret")
init_db()


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper


PERIODO_TASA_ETIQUETAS = {
    0: "Base 360 días",
    1: "Cada dos meses",
    2: "Mensual (el porcentaje ya es la tasa mensual)",
    3: "Semestral",
    4: "Cuatrimestral",
    5: "Trimestral",
    6: "Bimestral",
    7: "Anual (se convierte a tasa mensual)",
}


def etiqueta_periodo_tasa(valor) -> str:
    try:
        clave = int(valor)
    except (TypeError, ValueError):
        clave = 7
    return PERIODO_TASA_ETIQUETAS.get(clave, PERIODO_TASA_ETIQUETAS[7])


def etiqueta_capitalizacion(valor) -> str:
    if valor is None or valor == "":
        return "—"
    try:
        c = int(valor)
    except (TypeError, ValueError):
        return str(valor)
    nombres = {
        1: "Una vez al año",
        2: "Semestral",
        4: "Trimestral",
        12: "Mensual",
    }
    return nombres.get(c, f"{c} veces al año")


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
        password2 = request.form.get("password_confirm", "").strip()
        dni = request.form.get("dni_usuario", "").strip()
        if not username or not password:
            flash("Completa usuario y contraseña.")
            return render_template("register.html")
        if password != password2:
            flash("Las contraseñas no coinciden.")
            return render_template("register.html")
        if len(username) < 3 or len(username) > 50:
            flash("El usuario debe tener entre 3 y 50 caracteres.")
            return render_template("register.html")
        if len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.")
            return render_template("register.html")
        if not re.fullmatch(r"\d{8}", dni):
            flash("El DNI debe tener exactamente 8 dígitos.")
            return render_template("register.html")

        conn = get_conn()
        try:
            dup = conn.execute(
                "SELECT 1 FROM usuario WHERE usuario_login = ? OR dni_usuario = ?",
                (username, dni),
            ).fetchone()
            if dup:
                flash("Ese usuario o DNI ya está registrado.")
                return render_template("register.html")
            conn.execute(
                "INSERT INTO usuario (usuario_login, password_hash, dni_usuario) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), dni),
            )
            conn.commit()
            flash("Cuenta creada. Ahora inicia sesión.")
            return redirect(url_for("login"))
        except Exception:
            flash("No se pudo registrar. Intenta con otro usuario o DNI.")
            return render_template("register.html")
        finally:
            conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_conn()
        user = conn.execute(
            "SELECT * FROM usuario WHERE usuario_login = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id_usuario"]
            session["username"] = user["usuario_login"]
            raw_dni = user["dni_usuario"] if "dni_usuario" in user.keys() else None
            session["dni"] = (raw_dni or "").strip() if raw_dni is not None else ""
            return redirect(url_for("dashboard"))
        flash("Credenciales inválidas.")
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def _list_creditos(id_usuario):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT c.id_credito AS id, cl.nombre_cliente, cl.apellido_cliente, v.marca_vehiculo, v.modelo_vehiculo, c.created_at
        FROM credito c
        JOIN cliente cl ON c.id_cliente = cl.id_cliente
        JOIN vehiculo v ON c.id_vehiculo = v.id_vehiculo
        WHERE cl.id_usuario = ?
        ORDER BY c.id_credito DESC
        """,
        (id_usuario,),
    ).fetchall()
    conn.close()
    return rows


def _upsert_cliente(conn, id_usuario, nombres, apellidos, dni, correo, telefono, direccion, ingresos):
    row = conn.execute(
        "SELECT id_cliente FROM cliente WHERE id_usuario = ? ORDER BY id_cliente ASC LIMIT 1",
        (id_usuario,),
    ).fetchone()
    if row:
        cid = row["id_cliente"]
        conn.execute(
            """
            UPDATE cliente SET nombre_cliente=?, apellido_cliente=?, dni_cliente=?, correo_cliente=?, telefono_cliente=?,
            direccion_cliente=?, ingresos_mensuales=? WHERE id_cliente=?
            """,
            (nombres, apellidos, dni, correo, telefono, direccion, ingresos, cid),
        )
        return cid
    cur = conn.execute(
        """
        INSERT INTO cliente (id_usuario, nombre_cliente, apellido_cliente, dni_cliente, correo_cliente,
            telefono_cliente, direccion_cliente, ingresos_mensuales)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (id_usuario, nombres, apellidos, dni, correo, telefono, direccion, ingresos),
    )
    return cur.lastrowid


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    uid = session["user_id"]
    if request.method == "POST":
        try:
            dni_cuenta = (session.get("dni") or "").strip()
            if not dni_cuenta:
                flash("Tu cuenta no tiene DNI asociado. Crea una cuenta nueva o contacta al administrador.")
                return render_template(
                    "dashboard.html",
                    plans=_list_creditos(session["user_id"]),
                    username=session.get("username", ""),
                    dni_cuenta=session.get("dni", ""),
                )
            nombres_cliente = request.form["nombres_cliente"].strip()[:100]
            apellidos_cliente = request.form["apellidos_cliente"].strip()[:100]
            correo_cliente = request.form.get("correo_cliente", "").strip()[:150]
            telefono_cliente = request.form.get("telefono_cliente", "").strip()[:20]
            direccion_cliente = request.form.get("direccion_cliente", "").strip()[:200]
            ingresos_mensuales = float(request.form["ingresos_mensuales"])
            marca_vehiculo = request.form["marca_vehiculo"].strip()[:50]
            modelo_vehiculo = request.form["modelo_vehiculo"].strip()[:50]
            precio_vehiculo = float(request.form["precio_vehiculo"])
            cuota_inicial_pct = float(request.form["cuota_inicial_pct"])
            moneda = request.form["moneda"]
            tipo_tasa = request.form["tipo_tasa"]
            tasa_interes = float(request.form["tasa_interes"]) / 100.0
            capitalizacion_raw = request.form.get("capitalizacion", "").strip()
            capitalizacion = int(capitalizacion_raw) if capitalizacion_raw else None
            periodo_tasa = int(request.form.get("periodo_tasa", "7"))
            plazo_meses = int(request.form["plazo_meses"])
            periodo_gracia = request.form["periodo_gracia"]
            meses_gracia = int(request.form.get("meses_gracia", 0))
            seguro_desgravamen = float(request.form["seguro_desgravamen"]) / 100.0
            seguro_vehicular = float(request.form["seguro_vehicular"]) / 100.0
            portes = float(request.form["portes"])
            fecha_desembolso = request.form.get("fecha_desembolso", "").strip()

            # Validaciones de negocio
            if not nombres_cliente or not apellidos_cliente:
                raise ValueError("Nombres y apellidos son obligatorios.")
            if moneda not in ("Soles", "Dólares"):
                raise ValueError("Moneda inválida.")
            if tipo_tasa not in ("Efectiva", "Nominal"):
                raise ValueError("Tipo de tasa inválido.")
            if periodo_tasa < 0 or periodo_tasa > 7:
                periodo_tasa = 7
            if tipo_tasa == "Nominal" and (capitalizacion is None or capitalizacion < 1):
                raise ValueError("Para tasa nominal es obligatorio indicar la capitalización (≥ 1).")
            if precio_vehiculo <= 0:
                raise ValueError("El precio del vehículo debe ser mayor a 0.")
            if not (0 <= cuota_inicial_pct < 100):
                raise ValueError("La cuota inicial debe estar entre 0 % y 99 %.")
            if tasa_interes <= 0:
                raise ValueError("La tasa de interés debe ser mayor a 0.")
            if plazo_meses < 1 or plazo_meses > 480:
                raise ValueError("El plazo debe estar entre 1 y 480 meses.")
            if periodo_gracia not in ("Ninguno", "Parcial", "Total"):
                raise ValueError("Periodo de gracia inválido.")
            if meses_gracia < 0 or meses_gracia >= plazo_meses:
                raise ValueError("Los meses de gracia deben ser menores al plazo total.")
            if ingresos_mensuales < 0:
                raise ValueError("Los ingresos mensuales no pueden ser negativos.")
            if seguro_desgravamen < 0 or seguro_vehicular < 0 or portes < 0:
                raise ValueError("Seguros y portes no pueden ser negativos.")
            if not fecha_desembolso or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha_desembolso):
                raise ValueError("La fecha de desembolso es obligatoria (formato AAAA-MM-DD).")

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
                periodo_tasa=periodo_tasa,
            )

            conn = get_conn()
            cur = conn.cursor()
            id_cliente = _upsert_cliente(
                conn,
                uid,
                nombres_cliente,
                apellidos_cliente,
                dni_cuenta,
                correo_cliente,
                telefono_cliente,
                direccion_cliente,
                ingresos_mensuales,
            )

            cur.execute(
                """
                INSERT INTO vehiculo (marca_vehiculo, modelo_vehiculo, precio_vehiculo)
                VALUES (?, ?, ?)
                """,
                (marca_vehiculo, modelo_vehiculo, precio_vehiculo),
            )
            id_vehiculo = cur.lastrowid

            cur.execute(
                """
                INSERT INTO credito (
                    id_cliente, id_vehiculo, moneda, tipo_tasa, tasa_interes, capitalizacion, periodo_tasa, plazo_meses,
                    periodo_gracia, meses_gracia, cuota_inicial, fecha_desembolso, tem, cuota_base, total_financiado, flujo_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id_cliente,
                    id_vehiculo,
                    moneda,
                    tipo_tasa,
                    tasa_interes,
                    capitalizacion,
                    periodo_tasa,
                    plazo_meses,
                    periodo_gracia,
                    meses_gracia,
                    cuota_inicial_pct,
                    fecha_desembolso,
                    result.tem,
                    result.cuota_base,
                    result.saldo_inicial,
                    json.dumps(result.flujo),
                ),
            )
            id_credito = cur.lastrowid

            cur.execute(
                """
                INSERT INTO seguro (id_credito, seguro_desgravamen, seguro_vehicular, portes)
                VALUES (?, ?, ?, ?)
                """,
                (id_credito, seguro_desgravamen, seguro_vehicular, portes),
            )

            cur.execute(
                """
                INSERT INTO indicadores_financieros (id_credito, van, tir, tcea, tem)
                VALUES (?, ?, ?, ?, ?)
                """,
                (id_credito, result.van, result.tir, result.tcea, result.tem),
            )

            for row in result.schedule:
                cur.execute(
                    """
                    INSERT INTO cronograma_pago (
                        id_credito, numero_cuota, cuota_base, interes_periodo, amortizacion_periodo,
                        saldo_pendiente, cuota_total, seguro_cuota, portes_cuota
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_credito,
                        row.periodo,
                        result.cuota_base,
                        row.interes,
                        row.amortizacion,
                        row.saldo_final,
                        row.cuota_total,
                        row.seguro,
                        row.portes,
                    ),
                )

            conn.commit()
            conn.close()
            return redirect(url_for("plan_detail", credito_id=id_credito))
        except Exception as exc:
            flash(f"Error en cálculo o registro: {exc}")

    return render_template(
        "dashboard.html",
        plans=_list_creditos(uid),
        username=session.get("username", ""),
        dni_cuenta=session.get("dni", ""),
    )


@app.get("/plans/<int:credito_id>")
@login_required
def plan_detail(credito_id: int):
    conn = get_conn()
    row = conn.execute(
        """
        SELECT c.*, cl.nombre_cliente, cl.apellido_cliente, cl.dni_cliente,
               v.marca_vehiculo, v.modelo_vehiculo, i.van, i.tir, i.tcea
        FROM credito c
        JOIN cliente cl ON c.id_cliente = cl.id_cliente
        JOIN vehiculo v ON c.id_vehiculo = v.id_vehiculo
        LEFT JOIN indicadores_financieros i ON c.id_credito = i.id_credito
        WHERE c.id_credito = ? AND cl.id_usuario = ?
        """,
        (credito_id, session["user_id"]),
    ).fetchone()
    schedule = conn.execute(
        """
        SELECT numero_cuota AS periodo, cuota_base, interes_periodo AS interes, amortizacion_periodo AS amortizacion,
               saldo_pendiente AS saldo_final, cuota_total, seguro_cuota AS seguro, portes_cuota AS portes
        FROM cronograma_pago WHERE id_credito = ? ORDER BY numero_cuota ASC
        """,
        (credito_id,),
    ).fetchall()
    conn.close()
    if not row:
        flash("Crédito no encontrado.")
        return redirect(url_for("dashboard"))
    periodo_tasa = row["periodo_tasa"] if "periodo_tasa" in row.keys() else 7
    cap = row["capitalizacion"] if "capitalizacion" in row.keys() else None
    return render_template(
        "plan_detail.html",
        plan=row,
        schedule=schedule,
        periodo_tasa_etiqueta=etiqueta_periodo_tasa(periodo_tasa),
        capitalizacion_etiqueta=etiqueta_capitalizacion(cap),
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port)
