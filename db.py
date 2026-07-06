"""Base de datos SQLite — FinanCuota. gorje."""

import os
import sqlite3
from pathlib import Path


_default_db = Path(__file__).resolve().parent / "financuota.db"
_env_db = os.environ.get("FINANCUOTA_DB_PATH") or os.environ.get("DATABASE_PATH")
DB_PATH = Path(_env_db).expanduser() if _env_db else _default_db
if DB_PATH.parent:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    # Migrar esquema MVP antiguo (users / plans)
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('plans', 'users')"
    )
    if cur.fetchone():
        cur.executescript(
            """
            DROP TABLE IF EXISTS plan_schedule;
            DROP TABLE IF EXISTS plans;
            DROP TABLE IF EXISTS users;
            """
        )
        conn.commit()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'")
    if not cur.fetchone():
        cur.executescript(
        """
        CREATE TABLE usuario (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_login TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            dni_usuario CHAR(8) NOT NULL UNIQUE,
            rol TEXT NOT NULL DEFAULT 'usuario',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE cliente (
            id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario INTEGER NOT NULL,
            nombre_cliente TEXT NOT NULL,
            apellido_cliente TEXT NOT NULL,
            dni_cliente CHAR(8) NOT NULL,
            correo_cliente TEXT,
            telefono_cliente TEXT,
            direccion_cliente TEXT,
            ingresos_mensuales REAL NOT NULL,
            UNIQUE (id_usuario),
            FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
        );

        CREATE TABLE vehiculo (
            id_vehiculo INTEGER PRIMARY KEY AUTOINCREMENT,
            marca_vehiculo TEXT NOT NULL,
            modelo_vehiculo TEXT NOT NULL,
            precio_vehiculo REAL NOT NULL
        );

        CREATE TABLE credito (
            id_credito INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cliente INTEGER NOT NULL,
            id_vehiculo INTEGER NOT NULL,
            moneda TEXT NOT NULL,
            tipo_tasa TEXT NOT NULL,
            tasa_interes REAL NOT NULL,
            capitalizacion INTEGER,
            periodo_tasa INTEGER NOT NULL DEFAULT 7,
            plazo_meses INTEGER NOT NULL,
            periodo_gracia TEXT NOT NULL,
            meses_gracia INTEGER NOT NULL,
            cuota_inicial REAL NOT NULL,
            fecha_desembolso TEXT NOT NULL,
            tem REAL NOT NULL,
            cuota_base REAL NOT NULL,
            total_financiado REAL NOT NULL,
            flujo_json TEXT NOT NULL,
            modalidad TEXT NOT NULL DEFAULT 'Convencional',
            cuota_balon_pct REAL NOT NULL DEFAULT 0,
            cuota_balon_monto REAL NOT NULL DEFAULT 0,
            gastos_notariales REAL NOT NULL DEFAULT 0,
            gastos_registrales REAL NOT NULL DEFAULT 0,
            costos_iniciales REAL NOT NULL DEFAULT 0,
            tipo_cambio REAL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente),
            FOREIGN KEY (id_vehiculo) REFERENCES vehiculo(id_vehiculo)
        );

        CREATE TABLE seguro (
            id_seguro INTEGER PRIMARY KEY AUTOINCREMENT,
            id_credito INTEGER NOT NULL UNIQUE,
            seguro_desgravamen REAL NOT NULL,
            seguro_vehicular REAL NOT NULL,
            portes REAL NOT NULL,
            FOREIGN KEY (id_credito) REFERENCES credito(id_credito) ON DELETE CASCADE
        );

        CREATE TABLE indicadores_financieros (
            id_indicador INTEGER PRIMARY KEY AUTOINCREMENT,
            id_credito INTEGER NOT NULL UNIQUE,
            van REAL,
            tir REAL,
            tcea REAL,
            tem REAL,
            FOREIGN KEY (id_credito) REFERENCES credito(id_credito) ON DELETE CASCADE
        );

        CREATE TABLE cronograma_pago (
            id_pago INTEGER PRIMARY KEY AUTOINCREMENT,
            id_credito INTEGER NOT NULL,
            numero_cuota INTEGER NOT NULL,
            cuota_base REAL NOT NULL,
            interes_periodo REAL NOT NULL,
            amortizacion_periodo REAL NOT NULL,
            saldo_pendiente REAL NOT NULL,
            cuota_total REAL NOT NULL,
            seguro_cuota REAL NOT NULL DEFAULT 0,
            portes_cuota REAL NOT NULL DEFAULT 0,
            cuota_balon REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (id_credito) REFERENCES credito(id_credito) ON DELETE CASCADE
        );

        CREATE INDEX idx_credito_cliente ON credito(id_cliente);
        CREATE INDEX idx_cronograma_credito ON cronograma_pago(id_credito);
        """
        )
        conn.commit()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='credito'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(credito)")
        cols = [row[1] for row in cur.fetchall()]
        credito_migrations = {
            "periodo_tasa": "ALTER TABLE credito ADD COLUMN periodo_tasa INTEGER DEFAULT 7",
            "modalidad": "ALTER TABLE credito ADD COLUMN modalidad TEXT DEFAULT 'Convencional'",
            "cuota_balon_pct": "ALTER TABLE credito ADD COLUMN cuota_balon_pct REAL DEFAULT 0",
            "cuota_balon_monto": "ALTER TABLE credito ADD COLUMN cuota_balon_monto REAL DEFAULT 0",
            "gastos_notariales": "ALTER TABLE credito ADD COLUMN gastos_notariales REAL DEFAULT 0",
            "gastos_registrales": "ALTER TABLE credito ADD COLUMN gastos_registrales REAL DEFAULT 0",
            "costos_iniciales": "ALTER TABLE credito ADD COLUMN costos_iniciales REAL DEFAULT 0",
            "tipo_cambio": "ALTER TABLE credito ADD COLUMN tipo_cambio REAL",
        }
        for col, sql in credito_migrations.items():
            if col not in cols:
                cur.execute(sql)
        conn.commit()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cronograma_pago'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(cronograma_pago)")
        ccols = [row[1] for row in cur.fetchall()]
        if "cuota_balon" not in ccols:
            cur.execute("ALTER TABLE cronograma_pago ADD COLUMN cuota_balon REAL DEFAULT 0")
            conn.commit()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(usuario)")
        ucols = [row[1] for row in cur.fetchall()]
        if "dni_usuario" not in ucols:
            cur.execute("ALTER TABLE usuario ADD COLUMN dni_usuario CHAR(8)")
            conn.commit()
        if "rol" not in ucols:
            cur.execute("ALTER TABLE usuario ADD COLUMN rol TEXT NOT NULL DEFAULT 'usuario'")
            conn.commit()

    conn.close()
