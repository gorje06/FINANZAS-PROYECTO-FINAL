"""Base de datos SQLite — FinanCuota. gorje."""

import os
import sqlite3
from pathlib import Path
from typing import Any


_default_db = Path(__file__).resolve().parent / "financuota.db"
_env_db = os.environ.get("FINANCUOTA_DB_PATH") or os.environ.get("DATABASE_PATH")
DB_PATH = Path(_env_db).expanduser() if _env_db else _default_db
if DB_PATH.parent:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

TURSO_DATABASE_URL = (os.environ.get("TURSO_DATABASE_URL") or "").strip()
TURSO_AUTH_TOKEN = (os.environ.get("TURSO_AUTH_TOKEN") or "").strip()
USE_TURSO = bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)


def database_backend() -> str:
    return "turso" if USE_TURSO else "local"


def get_conn() -> Any:
    if USE_TURSO:
        from turso_http import connect_turso

        return connect_turso(TURSO_DATABASE_URL, TURSO_AUTH_TOKEN)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _row_value(row, key: str, index: int):
    try:
        raw = row[key]
    except (KeyError, TypeError, IndexError):
        raw = row[index]
    if isinstance(raw, dict):
        raw = raw.get("value", raw.get("name"))
    return raw


def _table_columns(conn, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    cols: set[str] = set()
    for row in rows:
        name = _row_value(row, "name", 1)
        if name is not None:
            cols.add(str(name))
    return cols


def _safe_add_column(conn, table: str, column: str, sql: str) -> None:
    if column in _table_columns(conn, table):
        return
    try:
        conn.execute(sql)
    except sqlite3.OperationalError as exc:
        if "duplicate column" not in str(exc).lower():
            raise
    except RuntimeError as exc:
        if "duplicate column" not in str(exc).lower():
            raise


def _sql_int(value, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


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
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
        );

        CREATE TABLE vehiculo (
            id_vehiculo INTEGER PRIMARY KEY AUTOINCREMENT,
            id_catalogo INTEGER,
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
        CREATE INDEX idx_cliente_usuario ON cliente(id_usuario);
        """
        )
        conn.commit()

    _migrate_cliente_schema(conn)
    _safe_add_column(
        conn,
        "vehiculo",
        "id_catalogo",
        "ALTER TABLE vehiculo ADD COLUMN id_catalogo INTEGER",
    )
    _safe_add_column(
        conn,
        "cliente",
        "created_at",
        "ALTER TABLE cliente ADD COLUMN created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
    )
    conn.commit()

    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='credito'").fetchone():
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
            _safe_add_column(conn, "credito", col, sql)
        conn.commit()

    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cronograma_pago'").fetchone():
        _safe_add_column(
            conn,
            "cronograma_pago",
            "cuota_balon",
            "ALTER TABLE cronograma_pago ADD COLUMN cuota_balon REAL DEFAULT 0",
        )
        conn.commit()

    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'").fetchone():
        _safe_add_column(
            conn,
            "usuario",
            "dni_usuario",
            "ALTER TABLE usuario ADD COLUMN dni_usuario CHAR(8)",
        )
        _safe_add_column(
            conn,
            "usuario",
            "rol",
            "ALTER TABLE usuario ADD COLUMN rol TEXT NOT NULL DEFAULT 'usuario'",
        )
        _safe_add_column(
            conn,
            "usuario",
            "correo_usuario",
            "ALTER TABLE usuario ADD COLUMN correo_usuario TEXT",
        )
        conn.commit()

    if not conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='catalogo_vehiculo'").fetchone():
        conn.executescript(
            """
            CREATE TABLE catalogo_vehiculo (
                id_catalogo INTEGER PRIMARY KEY AUTOINCREMENT,
                marca TEXT NOT NULL,
                modelo TEXT NOT NULL,
                anio INTEGER NOT NULL,
                variante TEXT NOT NULL,
                categoria TEXT NOT NULL,
                combustible TEXT NOT NULL DEFAULT 'Gasolina',
                condicion TEXT NOT NULL DEFAULT 'Nuevo',
                descripcion TEXT,
                precio REAL NOT NULL,
                imagen_url TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX idx_catalogo_categoria ON catalogo_vehiculo(categoria);
            """
        )
        conn.commit()

    _ensure_catalogo(conn)

    conn.close()


def _ensure_catalogo(conn) -> None:
    """Inserta o actualiza los vehículos base del catálogo (idempotente, compatible Turso)."""
    for item in CATALOGO_VEHICULOS:
        marca, modelo, anio, variante, categoria, combustible, condicion, descripcion, precio, imagen_url = (
            _catalogo_row_tuple(item)
        )
        row = conn.execute(
            "SELECT id_catalogo FROM catalogo_vehiculo WHERE marca = ? AND modelo = ? LIMIT 1",
            (marca, modelo),
        ).fetchone()
        if row:
            conn.execute(
                """
                UPDATE catalogo_vehiculo SET
                    anio=?, variante=?, categoria=?, combustible=?, condicion=?,
                    descripcion=?, precio=?, imagen_url=?
                WHERE id_catalogo=?
                """,
                (
                    anio,
                    variante,
                    categoria,
                    combustible,
                    condicion,
                    descripcion,
                    precio,
                    imagen_url,
                    row["id_catalogo"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO catalogo_vehiculo (
                    marca, modelo, anio, variante, categoria, combustible, condicion,
                    descripcion, precio, imagen_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    marca,
                    modelo,
                    anio,
                    variante,
                    categoria,
                    combustible,
                    condicion,
                    descripcion,
                    precio,
                    imagen_url,
                ),
            )
    conn.commit()


def catalogo_count(conn=None) -> int:
    own = conn is None
    if own:
        conn = get_conn()
    row = conn.execute("SELECT COUNT(*) AS n FROM catalogo_vehiculo").fetchone()
    count = _sql_int(row["n"] if row else 0)
    if own:
        conn.close()
    return count


def _migrate_cliente_schema(conn) -> None:
    """Quita UNIQUE(id_usuario) para permitir varios clientes por vendedor."""
    has_cliente = bool(
        conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cliente'"
        ).fetchone()
    )
    has_migracion = bool(
        conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cliente_migracion'"
        ).fetchone()
    )

    if not has_cliente and has_migracion:
        conn.executescript(
            """
            ALTER TABLE cliente_migracion RENAME TO cliente;
            CREATE INDEX IF NOT EXISTS idx_cliente_usuario ON cliente(id_usuario);
            """
        )
        conn.commit()
        has_cliente = True
        has_migracion = False

    if not has_cliente:
        return

    if has_migracion:
        conn.execute("DROP TABLE IF EXISTS cliente_migracion")
        conn.commit()

    ddl_row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='cliente'"
    ).fetchone()
    if not ddl_row:
        return
    ddl = str(_row_value(ddl_row, "sql", 0) or "").upper()
    if "UNIQUE" not in ddl or "ID_USUARIO" not in ddl:
        return
    has_created_at = "created_at" in _table_columns(conn, "cliente")
    created_select = "created_at" if has_created_at else "CURRENT_TIMESTAMP"
    conn.executescript(
        f"""
        PRAGMA foreign_keys=OFF;
        DROP TABLE IF EXISTS cliente_migracion;
        CREATE TABLE cliente_migracion (
            id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario INTEGER NOT NULL,
            nombre_cliente TEXT NOT NULL,
            apellido_cliente TEXT NOT NULL,
            dni_cliente CHAR(8) NOT NULL,
            correo_cliente TEXT,
            telefono_cliente TEXT,
            direccion_cliente TEXT,
            ingresos_mensuales REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
        );
        INSERT INTO cliente_migracion (
            id_cliente, id_usuario, nombre_cliente, apellido_cliente, dni_cliente,
            correo_cliente, telefono_cliente, direccion_cliente, ingresos_mensuales, created_at
        )
        SELECT
            id_cliente, id_usuario, nombre_cliente, apellido_cliente, dni_cliente,
            correo_cliente, telefono_cliente, direccion_cliente, ingresos_mensuales,
            {created_select}
        FROM cliente;
        DROP TABLE cliente;
        ALTER TABLE cliente_migracion RENAME TO cliente;
        CREATE INDEX IF NOT EXISTS idx_cliente_usuario ON cliente(id_usuario);
        PRAGMA foreign_keys=ON;
        """
    )
    conn.commit()


CATALOGO_VEHICULOS = [
    {
        "marca": "BMW",
        "modelo": "M3",
        "anio": 2025,
        "variante": "Competition M xDrive",
        "categoria": "Deportivo",
        "combustible": "Gasolina",
        "condicion": "Nuevo",
        "descripcion": (
            "Sedán deportivo de altas prestaciones con motor biturbo de 6 cilindros en línea, "
            "510 HP y tracción integral xDrive. Transmisión automática de 8 velocidades, "
            "frenos M Compound y paquete aerodinámico M. Ideal para quien busca máximo "
            "rendimiento con uso diario."
        ),
        "precio": 380000.0,
        "imagen": "bmw-m3.jpg",
    },
    {
        "marca": "Chevrolet",
        "modelo": "Camaro",
        "anio": 2024,
        "variante": "SS 6.2L V8",
        "categoria": "Deportivo",
        "combustible": "Gasolina",
        "condicion": "Nuevo",
        "descripcion": (
            "Muscle car americano con motor V8 atmosférico de 6.2 L y 455 HP. "
            "Tracción trasera, caja automática de 10 velocidades y modo de manejo deportivo. "
            "Diseño agresivo con amplio equipamiento de seguridad activa."
        ),
        "precio": 285000.0,
        "imagen": "camaro.jpg",
    },
    {
        "marca": "Ford",
        "modelo": "Mustang",
        "anio": 2024,
        "variante": "GT Premium 5.0 V8",
        "categoria": "Deportivo",
        "combustible": "Gasolina",
        "condicion": "Nuevo",
        "descripcion": (
            "Ícono deportivo con motor Coyote V8 de 5.0 L, 486 HP y escape activo. "
            "Versión Premium con cuero, pantalla central de 13.4\" y asistencias Ford Co-Pilot360. "
            "Experiencia de conducción pura con tecnología moderna."
        ),
        "precio": 310000.0,
        "imagen": "mustang.jpg",
    },
    {
        "marca": "Porsche",
        "modelo": "911",
        "anio": 2024,
        "variante": "Carrera S",
        "categoria": "Deportivo",
        "combustible": "Gasolina",
        "condicion": "Nuevo",
        "descripcion": (
            "Deportivo de motor trasero con 443 HP, chasis deportivo y tracción trasera. "
            "Acabado premium en cuero, sistema PCM con navegación y paquete Sport Chrono. "
            "Referente en prestaciones y valor de reventa en el segmento premium."
        ),
        "precio": 598000.0,
        "imagen": "porsche-911.jpg",
    },
    {
        "marca": "Toyota",
        "modelo": "RAV4",
        "anio": 2025,
        "variante": "XLE Hybrid",
        "categoria": "SUV",
        "combustible": "Híbrido",
        "condicion": "Nuevo",
        "descripcion": (
            "SUV compacto híbrido con motor 2.5 L y sistema e-CVT. Consumo eficiente, "
            "tracción AWD-i y Toyota Safety Sense de serie. Amplio maletero y excelente "
            "reventa; opción familiar muy demandada en Perú."
        ),
        "precio": 168900.0,
        "imagen": "rav4.jpg",
    },
    {
        "marca": "Hyundai",
        "modelo": "Tucson",
        "anio": 2024,
        "variante": "Limited AWD",
        "categoria": "SUV",
        "combustible": "Gasolina",
        "condicion": "Nuevo",
        "descripcion": (
            "SUV mediano con diseño paramétrico, motor 2.5 L y tracción integral HTRAC. "
            "Pantalla curva de 12.3\", techo panorámico y asistencias Hyundai SmartSense. "
            "Relación equipamiento-precio competitiva en su segmento."
        ),
        "precio": 142500.0,
        "imagen": "tucson.jpg",
    },
    {
        "marca": "Mazda",
        "modelo": "CX-5",
        "anio": 2025,
        "variante": "Grand Touring",
        "categoria": "SUV",
        "combustible": "Gasolina",
        "condicion": "Nuevo",
        "descripcion": (
            "SUV premium con motor Skyactiv-G 2.5 L turbo, 256 HP y acabados en cuero Nappa. "
            "Manejo dinámico G-Vectoring Plus y sistema i-Activsense. Enfoque en "
            "conducción placentera y diseño elegante."
        ),
        "precio": 155800.0,
        "imagen": "cx5.jpg",
    },
    {
        "marca": "Kia",
        "modelo": "Sportage",
        "anio": 2024,
        "variante": "EX Plus",
        "categoria": "SUV",
        "combustible": "Gasolina",
        "condicion": "Nuevo",
        "descripcion": (
            "SUV versátil con motor 2.0 L, pantallas duales de 12.3\" y conectividad inalámbrica. "
            "Paquete de asistencias Drive Wise y garantía de fábrica extendida. "
            "Buena opción urbana con espacio para familia."
        ),
        "precio": 134900.0,
        "imagen": "sportage.jpg",
    },
    {
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2026,
        "variante": "XEI 1.8",
        "categoria": "Sedán",
        "combustible": "Gasolina",
        "condicion": "Nuevo",
        "descripcion": (
            "Sedán confiable con motor 1.8 L, transmisión CVT y bajo costo de mantenimiento. "
            "Toyota Safety Sense, amplio espacio trasero y excelente reventa. "
            "Vehículo del caso de prueba Carlos Ramírez (S/ 85,000 — informe cap. 3.4)."
        ),
        "precio": 85000.0,
        "imagen": "corolla.jpg",
    },
    {
        "marca": "Honda",
        "modelo": "Civic",
        "anio": 2025,
        "variante": "Touring 1.5 Turbo",
        "categoria": "Sedán",
        "combustible": "Gasolina",
        "condicion": "Nuevo",
        "descripcion": (
            "Sedán compacto deportivo con turbo 1.5 L, 180 HP y transmisión CVT. "
            "Honda Sensing, asientos de cuero y audio Bose de 12 bocinas. "
            "Equilibrio entre deportividad y eficiencia para uso diario."
        ),
        "precio": 128500.0,
        "imagen": "civic.jpg",
    },
    {
        "marca": "Hyundai",
        "modelo": "Elantra",
        "anio": 2024,
        "variante": "GL 2.0",
        "categoria": "Sedán",
        "combustible": "Gasolina",
        "condicion": "Nuevo",
        "descripcion": (
            "Sedán accesible con motor 2.0 L, diseño moderno y garantía de 5 años. "
            "Buen equipamiento de serie: cámara de retroceso, control de crucero y "
            "conectividad Apple CarPlay / Android Auto."
        ),
        "precio": 94900.0,
        "imagen": "elantra.jpg",
    },
    {
        "marca": "Nissan",
        "modelo": "Sentra",
        "anio": 2025,
        "variante": "Advance 2.0",
        "categoria": "Sedán",
        "combustible": "Gasolina",
        "condicion": "Nuevo",
        "descripcion": (
            "Sedán familiar con motor 2.0 L, maletero amplio y suspensión confortable. "
            "Nissan Safety Shield 360 y pantalla táctil de 8\". Opción práctica para "
            "trabajo y familia con cuotas accesibles."
        ),
        "precio": 98900.0,
        "imagen": "sentra.jpg",
    },
]


def _catalogo_row_tuple(item: dict) -> tuple:
    return (
        item["marca"],
        item["modelo"],
        item["anio"],
        item["variante"],
        item["categoria"],
        item["combustible"],
        item["condicion"],
        item["descripcion"],
        item["precio"],
        f"/static/catalog/{item['imagen']}",
    )
