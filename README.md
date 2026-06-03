# 🕒 Aplicativo de Tareo de Operaciones — PECEPE

Flujo completo, con un dashboard que funciona en **PC, celular y tablet**:

```
Archivo de carga (sistema de asistencia)
        │  se sube al aplicativo
        ▼
Supervisores aplican condiciones POR GRUPO  (Corrido, Teórico 12,
Refrigerio, Descuento extra, Jornada noche 19–07 / 20–08) y aprueban
        │  → se obtiene el intermedio
        ▼
REPORTE_TAREO_SISTEMA (tareo trabajado)   ← descargable en Excel
        │  mapeo + cálculo de horas extra
        ▼
REPORTE_OPERACIONES (producto final)      ← Excel idéntico al formato original
```

## ▶️ Cómo iniciarlo

**Opción fácil (Windows):** doble clic en **`INICIAR_APP.bat`**.
Se abrirá solo en el navegador.

**Opción manual:**
```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

### Usarlo desde el celular / tablet
Cuando inicie, muestra una **Network URL** (ej. `http://192.168.x.x:8501`).
Abre esa dirección en el navegador del celular/tablet **conectado a la misma red Wi-Fi**.

## 🔐 Control de acceso (usuarios)

Al abrir el aplicativo se pide **usuario y contraseña**. Hay dos roles:

- **Coordinador**: carga el archivo, ve y aprueba **todos los grupos**, genera el
  reporte final y administra los usuarios (pestaña *Usuarios*).
- **Supervisor**: sólo ve y autoriza **su grupo**.

**Usuarios iniciales** (cámbialos en la pestaña *Usuarios* tras el primer ingreso):

| Usuario | Contraseña | Rol | Grupo |
|---------|-----------|-----|-------|
| `coordinador` | `coord123` | Coordinador | (todos) |
| `sup_n` | `N123` | Supervisor | N |
| `sup_e` | `E123` | Supervisor | E |
| `sup_pcp` | `PCP123` | Supervisor | PCP |
| `sup_1` … `sup_5` | `1123` … `5123` | Supervisor | 1 … 5 |

Las contraseñas se guardan **cifradas** (SHA-256 + sal) en `usuarios.json`.

> **Trabajo en simultáneo:** todos los supervisores trabajan el **mismo tareo**
> (estado compartido en `estado_tareo.pkl`). Cada uno autoriza su grupo y el
> coordinador ve todo consolidado para emitir el reporte.

## 🧭 Flujo de trabajo (4 pestañas)

1. **📥 Cargar** — sube el `REPORTE_TAREO_SISTEMA.xlsx` (o usa el de la carpeta) y
   pulsa *Procesar tareo*. Detecta automáticamente la fila de cabecera.
2. **🧮 Condiciones / TTHH** — cada **supervisor filtra su grupo** y ajusta las
   condiciones que convierten las horas de marcación en **TTHH**:
   - **Acciones masivas** (sólo sobre el grupo filtrado): Corrido, Teórico 12,
     Refrigerio, Descuento extra 1/2/3 h, y **Jornada noche (19–07 o 20–08)**.
   - **Edición individual**: check por persona, incluyendo elegir la jornada de
     noche. El TTHH se recalcula al instante.
3. **✅ Aprobación por grupo** — cada supervisor selecciona **su grupo**, revisa
   las horas teóricas y **aprueba** (botón *Aprobar grupo*). Hay un tablero de
   avance por grupo. Solo lo aprobado pasa al reporte final.
4. **📤 Reporte final** — vista previa del **REPORTE_OPERACIONES** y descarga en
   **Excel** (con formato) o **CSV**.

## 📐 Reglas de cálculo (TTHH)

| Condición | Efecto |
|-----------|--------|
| Sin observación | Se descuentan **45 min** de refrigerio |
| **C** (Corrido) | **No** se descuenta refrigerio |
| **12** | TTHH = **12 h** exactas; INICIO/SALIDA teóricos (día 07–19; noche **19–07 o 20–08**, a elección) |
| **menos 1 / 2 / 3** | Descuenta esas horas **adicionales** |
| Grupos **E, PCP, N, 5** | **No** descuentan refrigerio (configurable en la barra lateral) |

**Horas extra del reporte final:**
- `hora normal`: hasta **8 h**
- `hora 25`: de 8 a **10 h** (máx. 2 h)
- `hora 35`: lo que exceda de 10 h
- `hora 100`: domingos/feriados (manual, queda en 0)
- `BONO HH`: manual

> Todas las reglas (minutos de refrigerio, grupos sin refrigerio, jornadas
> teóricas, PRODUCTO, ZONA) se editan en la **barra lateral** sin tocar el código.

## 📁 Archivos del proyecto

| Archivo | Descripción |
|---------|-------------|
| `app.py` | Dashboard (interfaz Streamlit) |
| `tareo_core.py` | Motor de cálculo y reglas de negocio |
| `INICIAR_APP.bat` | Lanzador para Windows |
| `requirements.txt` | Dependencias |

## ✅ Validación

El motor se validó contra tu `REPORTE_OPERACIONES.xlsx` real:
**159 de 160 registros coinciden exactamente** en TTHH y tramos de horas extra.
El único distinto corresponde a un ajuste manual puntual del archivo original.
