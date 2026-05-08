import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "financuota.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nombres_cliente TEXT NOT NULL,
            apellidos_cliente TEXT NOT NULL,
            dni_cliente TEXT NOT NULL,
            correo_cliente TEXT,
            telefono_cliente TEXT,
            direccion_cliente TEXT,
            ingresos_mensuales REAL NOT NULL,
            marca_vehiculo TEXT NOT NULL,
            modelo_vehiculo TEXT NOT NULL,
            precio_vehiculo REAL NOT NULL,
            cuota_inicial_pct REAL NOT NULL,
            moneda TEXT NOT NULL,
            tipo_tasa TEXT NOT NULL,
            tasa_interes REAL NOT NULL,
            capitalizacion INTEGER,
            plazo_meses INTEGER NOT NULL,
            periodo_gracia TEXT NOT NULL,
            meses_gracia INTEGER NOT NULL,
            seguro_desgravamen REAL NOT NULL,
            seguro_vehicular REAL NOT NULL,
            portes REAL NOT NULL,
            tem REAL NOT NULL,
            cuota_base REAL NOT NULL,
            van REAL NOT NULL,
            tir REAL NOT NULL,
            tcea REAL NOT NULL,
            total_financiado REAL NOT NULL,
            flujo_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS plan_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            periodo INTEGER NOT NULL,
            cuota_total REAL NOT NULL,
            interes REAL NOT NULL,
            amortizacion REAL NOT NULL,
            saldo_final REAL NOT NULL,
            seguro REAL NOT NULL,
            portes REAL NOT NULL,
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        );
        """
    )
    conn.commit()
    conn.close()
