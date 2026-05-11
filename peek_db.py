"""Uso: python peek_db.py — Vista rápida de tablas ERD (SQLite)."""
import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parent / "financuota.db"
if not db.exists():
    print(f"No existe {db}. Ejecuta la app una vez.")
    raise SystemExit(1)

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print("Tablas:", ", ".join(tables))
print()

for t in tables:
    n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {n} filas")

print("\n--- usuario (hasta 3) ---")
for row in cur.execute("SELECT id_usuario, usuario_login FROM usuario LIMIT 3"):
    print(dict(row))

print("\n--- credito + cliente (hasta 3) ---")
for row in cur.execute(
    """
    SELECT c.id_credito, cl.dni_cliente, v.marca_vehiculo, c.fecha_desembolso, c.moneda
    FROM credito c
    JOIN cliente cl ON c.id_cliente = cl.id_cliente
    JOIN vehiculo v ON c.id_vehiculo = v.id_vehiculo
    LIMIT 3
    """
):
    print(dict(row))

cid = cur.execute("SELECT id_credito FROM credito ORDER BY id_credito LIMIT 1").fetchone()
if cid:
    print("\n--- cronograma (primer crédito, 3 filas) ---")
    for row in cur.execute(
        "SELECT numero_cuota, cuota_total, saldo_pendiente FROM cronograma_pago WHERE id_credito=? ORDER BY numero_cuota LIMIT 3",
        (cid[0],),
    ):
        print(dict(row))

conn.close()
print(f"\nArchivo: {db}")
