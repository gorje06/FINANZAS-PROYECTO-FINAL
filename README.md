# FinanCuota — Simulador de Crédito Vehicular

**Trabajo Final** · Finanzas e Ingeniería Económica · SI642 · UPC · Grupo 2

Simulador web para la **entidad financiera** (ejecutivos de crédito vehicular): catálogo de vehículos, wizard de simulación, **Compra Inteligente** (cuota balón + método francés), costos notariales/registrales, cronograma, VAN/TIR/TCEA (perspectiva deudor) y panel de administración.

**Demo:** despliega en [Render](https://render.com) con base persistente en [Turso](https://turso.tech).

---

## Funcionalidades

- Login, registro y roles (ejecutivo de la entidad / admin)
- Catálogo de vehículos con fotos y precios
- Wizard en 4 pasos: cliente → vehículo → crédito → costos
- Modalidades: **Convencional** y **Compra Inteligente**
- Gracia total/parcial · Soles y dólares · TCEA / TEM / VAN / TIR
- Guardar, ver, editar y eliminar simulaciones
- Exportar cronograma (Excel/CSV)
- Casos de prueba: Carlos Ramírez (convencional) y María López (Compra Inteligente)

---

## Arranque local

Doble clic en **`run-local.bat`** o en PowerShell:

```powershell
.\run-local.ps1
```

Abre: **http://127.0.0.1:5000**

| Cuenta admin | Valor |
|--------------|-------|
| Usuario | `admin` |
| Contraseña | `adminupc` |

La base SQLite local se guarda en `financuota.db` (persiste al cerrar la app).

---

## Despliegue en Render (gratis)

Guía paso a paso: **`INSTRUCCIONES_RENDER.txt`**

Variables de entorno en Render:

| Variable | Descripción |
|----------|-------------|
| `TURSO_DATABASE_URL` | URL de la base Turso (`libsql://...`) |
| `TURSO_AUTH_TOKEN` | Token de autenticación Turso |
| `SECRET_KEY` | Clave secreta Flask |

---

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.12 · Flask |
| Base de datos | SQLite local · Turso (libSQL remoto) |
| Frontend | HTML · CSS · JavaScript · Chart.js |
| Hosting | Render |

---

## Estructura del proyecto

```
app.py          # Rutas y lógica web
finance.py      # Motor financiero (francés, balón, VAN/TIR/TCEA)
db.py           # Esquema y migraciones
turso_http.py   # Cliente HTTP para Turso
templates/      # Vistas Jinja
static/         # Estilos, JS e imágenes del catálogo
```

---
