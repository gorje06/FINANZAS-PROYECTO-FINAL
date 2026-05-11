"""Base de datos SQLite — FinanCuota. gorje."""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "financuota.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
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
        if "periodo_tasa" not in cols:
            cur.execute("ALTER TABLE credito ADD COLUMN periodo_tasa INTEGER DEFAULT 7")
            conn.commit()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(usuario)")
        ucols = [row[1] for row in cur.fetchall()]
        if "dni_usuario" not in ucols:
            cur.execute("ALTER TABLE usuario ADD COLUMN dni_usuario CHAR(8)")
            conn.commit()

    conn.close()
