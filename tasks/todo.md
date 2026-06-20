# Tareas: Supabase + Render + Dashboard + WhatsApp

## Plan
- [x] 1. Git local + `.gitignore` (con `.env`) + commit inicial
- [x] 2. `.env` local con `DATABASE_URL` (Supabase)
- [x] 3. `db.py` (engine, init_schema, usuarios, tareo, config)
- [x] 4. Integrar `auth.py` con DB (delegar + `ensure_defaults`)
- [x] 5. Integrar `app.py` y `tareo_core.py` (modo dual + subset writeback)
- [x] 6. Crear tablas en Supabase + verificar flujo local end-to-end
- [x] 7. Archivos de deploy: `requirements.txt`, `render.yaml`, `.python-version`, `.env.example`
- [x] 8. `Informe.md` + README + sección de revisión
- [ ] 9. Push a GitHub (repo conectado a Render) — pendiente de URL y autenticación

## Plan: Dashboard + WhatsApp
- [x] 10. Crear `dashboard_charts.py`: gráficos Plotly + helpers WhatsApp
- [x] 11. Agregar `plotly>=5.0` a `requirements.txt`
- [x] 12. Agregar pestaña `📊 Dashboard` en `app.py` (con filtros)
- [x] 13. Agregar pestaña `📱 Compartir` en `app.py` (WhatsApp wa.me links)
- [x] 14. Merge a `main` y push para despliegue en Render

## Plan: Sorteo al Azar (Raffle App)
- [x] 15. Crear archivo `sorteo.html` — aplicación web standalone con:
  - Carga de archivo Excel (.xlsx) con columnas: Nombre, Turno, Empresa
  - Selección de cantidad de ganadores
  - Efecto visual de nombres girando en pantalla
  - Conteo regresivo de 5 a 0
  - Botón para revelar ganadores uno por uno
  - Diseño profesional mobile-first (Android)
  - Lista final de ganadores con nombre, turno y empresa
- [x] 16. Commit y push del sorteo
- [x] 17. Agregar música de fondo, efectos de sonido y botón Ausente al sorteo

## Revisión

### Qué se hizo
- Se añadió una **capa de base de datos** (`db.py`) sobre Supabase/PostgreSQL con
  esquema idempotente (`usuarios`, `config`, `tareo`).
- `auth.py` y `app.py` ahora funcionan en **modo dual**: usan Supabase si hay
  `DATABASE_URL`, o archivos locales como respaldo offline.
- La persistencia del tareo es **por subconjunto** (`tareo_save_subset`): cada
  supervisor actualiza sólo las filas de su grupo, sin pisar a los demás.
- Se agregaron archivos de despliegue para **Render** (`render.yaml`,
  `requirements.txt`, `.python-version`) y de seguridad (`.env`, `.env.example`,
  `.gitignore`).
- Se documentó todo en `Informe.md` y `README.md`.

### Seguridad (CLAUDE.md)
- `.gitignore` con `.env` creado **antes** del primer commit; verificado con
  `git check-ignore .env`.
- Contraseña de Supabase sólo en `.env` local y en variables de Render.
- Contraseñas de usuarios con hash SHA-256 + sal; conexión DB con SSL.

### Verificación
- Tablas creadas en Supabase (PostgreSQL 17.6).
- Flujo end-to-end probado contra la DB: cargar `CARGA.xlsx` (160) → aprobar
  grupo N (53) → editar grupo 5 sin afectar a N → reporte final 18 columnas.
- App arranca con DB sin errores (HTTP 200).

### Pendiente
- **Push a GitHub** (tarea 9): requiere la URL del repo conectado a Render y la
  autenticación (gh CLI o token). El usuario autorizó el push.
- En Render: definir `DATABASE_URL` en *Environment* y desplegar.
