# Informe del Proyecto — Aplicativo de Tareo de Operaciones (PECEPE)

## 1. Resumen
Aplicativo web que automatiza el proceso de tareo de la planta: toma el archivo
crudo del sistema de asistencia (**CARGA / REPORTE_TAREO_SISTEMA**), permite que
cada supervisor aplique condiciones por grupo y apruebe, y genera el
**REPORTE_OPERACIONES** final exportable a Excel con el formato corporativo.
Funciona en PC, celular y tablet (navegador), con control de acceso por rol y
base de datos central en la nube.

## 2. Arquitectura

```
Archivo de carga (Excel del sistema de asistencia)
        │  (sube el Coordinador)
        ▼
[ App Streamlit ]  ──►  cálculo de TTHH y horas extra (motor)
        │
        ├─ Supervisores aprueban su grupo (condiciones)
        │
        ▼
[ Supabase / PostgreSQL ]  ◄── estado central compartido
        │
        ▼
REPORTE_OPERACIONES.xlsx (producto final, formato idéntico)
```

- **Frontend / UI:** Streamlit (Python) — interfaz responsiva para web y móvil.
- **Backend / lógica:** Python (motor de reglas y cálculo en `tareo_core.py`).
- **Base de datos:** Supabase (PostgreSQL 17) vía SQLAlchemy + psycopg2.
- **Autenticación:** módulo propio con hash SHA-256 + sal (`auth.py`).
- **Despliegue:** Render (servicio web), build con `requirements.txt`.
- **Control de versiones:** Git local; remoto en GitHub (conectado a Render).

## 3. Lenguajes y tecnologías

| Capa | Tecnología |
|------|-----------|
| Lenguaje principal | Python 3.12 |
| Interfaz de usuario | Streamlit |
| Procesamiento de datos | pandas |
| Lectura/escritura Excel | openpyxl |
| ORM / acceso a datos | SQLAlchemy 2.0 |
| Driver PostgreSQL | psycopg2-binary |
| Variables de entorno | python-dotenv |
| Base de datos | PostgreSQL (Supabase) |
| Hosting | Render |
| Versionado | Git / GitHub |

## 4. Archivos del proyecto

| Archivo | Rol |
|---------|-----|
| `app.py` | Dashboard Streamlit: login, pestañas, flujo completo |
| `tareo_core.py` | Motor de reglas (TTHH, horas extra, export Excel) |
| `db.py` | Capa de base de datos Supabase (esquema, usuarios, tareo, config) |
| `auth.py` | Control de acceso por rol (coordinador / supervisor por grupo) |
| `requirements.txt` | Dependencias |
| `render.yaml` | Configuración de despliegue en Render |
| `.python-version` | Versión de Python para Render |
| `.env.example` | Plantilla de variables (sin credenciales reales) |
| `.gitignore` | Excluye `.env`, estado local y secretos |
| `INICIAR_APP.bat` | Lanzador local en Windows |
| `README.md` | Manual de uso |
| `Informe.md` | Este informe |
| `tasks/todo.md` | Checklist y revisión del trabajo |

## 5. Base de datos (Supabase)

Tablas creadas automáticamente por `db.init_schema()` (idempotente):

- **`usuarios`** — `usuario` (PK), `salt`, `hash`, `rol`, `grupo`.
- **`config`** — `id` (PK=1), `data` (JSONB con las reglas globales).
- **`tareo`** — `id` (serial PK) y las columnas del tareo trabajado
  (datos, condiciones por persona y estado de aprobación).

**Concurrencia:** cada supervisor sólo actualiza las filas de su grupo
(`tareo_save_subset` hace `UPDATE ... WHERE id = ...`), por lo que el trabajo de
unos no pisa el de otros. El coordinador ve todo consolidado al recargar.

## 6. Reglas de negocio (cálculo de TTHH)

- Refrigerio de 45 min se descuenta salvo: grupos `E, PCP, N, 5`, observación
  `C` (corrido) u observación `12` (jornada teórica).
- `12` → TTHH = 12 h; inicio/salida teóricos (día 07–19; noche **19–07 o 20–08**,
  seleccionable masiva o individualmente).
- Descuento extra de 1/2/3 horas adicional al refrigerio.
- Horas extra: normal (≤8 h), 25 % (8–10 h), 35 % (resto), 100 % (manual), BONO HH.

El motor fue validado contra el reporte manual real: **159/160 registros**
coinciden exactamente en TTHH y tramos de horas extra.

## 7. Seguridad

- Credenciales **solo** en `.env` local y en variables de entorno de Render;
  nunca en el repositorio (`.env` está en `.gitignore` desde el primer commit).
- Contraseñas de usuarios almacenadas con **hash SHA-256 + sal** (no en claro).
- Conexión a la base de datos con **SSL** (`sslmode=require`).
- Control de acceso por rol: el supervisor sólo ve y autoriza su grupo.
- `.env.example` documenta las variables necesarias sin valores reales.

## 8. Despliegue

1. Repositorio en GitHub conectado al servicio de Render.
2. En Render → Environment: definir `DATABASE_URL` (cadena de Supabase con la
   contraseña real). **No** se versiona.
3. Build: `pip install -r requirements.txt`.
4. Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`.
5. URL pública: https://operaciones-ysvc.onrender.com

## 9. Estado de verificación

- Conexión a Supabase y creación de tablas: **OK** (PostgreSQL 17.6).
- Login y persistencia de usuarios en DB: **OK**.
- Flujo end-to-end (cargar → aprobar por grupo → consolidar → exportar): **OK**.
- Concurrencia (no pisar grupos ajenos): **OK**.
- Arranque de la app con DB sin errores: **OK** (HTTP 200).
- Formato Excel del REPORTE_OPERACIONES idéntico al original (18 columnas): **OK**.
