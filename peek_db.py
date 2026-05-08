"""Uso: python peek_db.py"""
import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parent / "financuota.db"
if not db.exists():
    print(f"No existe {db}. Ejecuta la app una vez para crearla.")
    raise SystemExit(1)

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print("Tablas:", ", ".join(tables))
print()

for t in tables:
    n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {n} filas")

print("\n--- users (hasta 5) ---")
for row in cur.execute("SELECT * FROM users LIMIT 5"):
    print(dict(row))

print("\n--- plans (hasta 3, columnas resumidas) ---")
for row in cur.execute(
    "SELECT id, user_id, nombres_cliente, precio_vehiculo, plazo_meses, created_at FROM plans LIMIT 3"
):
    print(dict(row))

print("\n--- plan_schedule (primer plan, 5 filas) ---")
pid = cur.execute("SELECT id FROM plans ORDER BY id LIMIT 1").fetchone()
if pid:
    for row in cur.execute(
        "SELECT periodo, cuota_total, interes, amortizacion, saldo_final FROM plan_schedule WHERE plan_id = ? ORDER BY periodo LIMIT 5",
        (pid[0],),
    ):
        print(dict(row))

conn.close()
print(f"\nArchivo: {db}")
