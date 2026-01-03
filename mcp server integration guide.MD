# Guía de Implementación - Servidor MCP para Reportes de Control de Acceso

## Descripción

Servidor MCP (Model Context Protocol) para consultar reportes de nómina y asistencia desde el sistema de Control de Acceso con Reconocimiento Facial.

**Enfoque:** Conexión directa a PostgreSQL para consultas de lectura optimizadas.

**Casos de uso:**
- Horas trabajadas por empleado (diario/semanal/mensual)
- Horas extras diurnas y nocturnas
- Recargos nocturnos
- Trabajo dominical y festivo
- Reportes de asistencia
- Alertas de límites semanales

---

## Configuración de Base de Datos

### Variables de Entorno

```env
# PostgreSQL - Sistema de Control de Acceso (Producción)
# Nota: Usar DATABASE_URL para conexiones síncronas (psycopg2) o DATABASE_URL_ASYNC para async (asyncpg)
DATABASE_URL=postgresql+psycopg2://cocson:Ia$10018084@coson-prod_control_acceso_coson:5432/acceso-cocson

# Driver asyncpg para conexiones async (recomendado para MCP)
DATABASE_URL_ASYNC=postgresql+asyncpg://cocson:Ia$10018084@coson-prod_control_acceso_coson:5432/acceso-cocson

# Zona horaria
TIMEZONE=America/Bogota
```

### Dependencias

```toml
# pyproject.toml
[project]
name = "mcp-reportes-acceso"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.0.0",
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
    "asyncpg>=0.29.0",
    "python-dotenv>=1.0.0",
    "pytz>=2024.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
mcp-reportes = "mcp_reportes.server:main"
```

---

## Esquema de Base de Datos

### Tabla: `empleados`
```sql
CREATE TABLE empleados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_empleado VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    telefono VARCHAR(20),
    departamento VARCHAR(50),
    cargo VARCHAR(50),
    liquida_dominical BOOLEAN DEFAULT FALSE,  -- Si cobra dominicales
    dia_descanso VARCHAR(20),                  -- Día de descanso semanal
    punto_trabajo VARCHAR(100),                -- Restaurante asignado
    foto_path VARCHAR(255),
    face_embedding TEXT,                       -- Embedding facial (JSON)
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tabla: `registros`
```sql
CREATE TABLE registros (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empleado_id UUID REFERENCES empleados(id),
    turno_id UUID,                             -- Legacy (nullable)
    jornada_id UUID,                           -- Legacy (nullable)
    tipo_registro VARCHAR(10) NOT NULL,        -- 'ENTRADA' | 'SALIDA'
    punto_trabajo VARCHAR(100) NOT NULL,       -- Restaurante del registro
    fecha_registro DATE NOT NULL,
    hora_registro TIME NOT NULL,
    timestamp_registro TIMESTAMP DEFAULT NOW(),
    confianza_reconocimiento DECIMAL(5,4),     -- 0.0000 a 1.0000
    foto_registro_path VARCHAR(255),
    enviado_webhook BOOLEAN DEFAULT FALSE,
    webhook_response TEXT,
    observaciones TEXT,                        -- '[FORZADO]' si es autocierre
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Tabla: `configuracion`
```sql
CREATE TABLE configuracion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clave VARCHAR(50) UNIQUE NOT NULL,
    valor TEXT NOT NULL,
    descripcion TEXT,
    tipo_dato VARCHAR(20) DEFAULT 'string',
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Configuraciones importantes para cálculos:
-- 'horas_semanales' = 48
-- 'max_horas_por_dia' = 10
-- 'valor_hora_ordinaria' = 5833.33
-- 'valor_hora_extra_diurna' = 7291.67
-- 'valor_hora_extra_nocturna' = 10208.33
```

---

## Herramientas MCP

### 1. `consultar_empleados`

**Propósito:** Listar empleados activos del sistema.

```python
@mcp.tool()
async def consultar_empleados(
    activos_solo: bool = True,
    restaurante: str = None,
    departamento: str = None
) -> list[dict]:
    """
    Lista empleados del sistema con filtros opcionales.

    Args:
        activos_solo: Solo empleados activos (default: True)
        restaurante: Filtrar por punto de trabajo (Bandidos|Sumo|Leños y Parrilla)
        departamento: Filtrar por departamento

    Returns:
        Lista de empleados con: id, codigo, nombre, apellido, cargo,
        departamento, punto_trabajo, liquida_dominical, dia_descanso
    """
```

**Query SQL:**
```sql
SELECT
    id,
    codigo_empleado,
    nombre,
    apellido,
    email,
    telefono,
    departamento,
    cargo,
    liquida_dominical,
    dia_descanso,
    punto_trabajo,
    activo,
    created_at
FROM empleados
WHERE activo = :activo
  AND (:restaurante IS NULL OR punto_trabajo = :restaurante)
  AND (:departamento IS NULL OR departamento = :departamento)
ORDER BY apellido, nombre;
```

---

### 2. `consultar_registros_fecha`

**Propósito:** Obtener registros de entrada/salida por fecha.

```python
@mcp.tool()
async def consultar_registros_fecha(
    fecha: str,
    empleado_id: str = None,
    restaurante: str = None,
    tipo: str = None
) -> list[dict]:
    """
    Consulta registros de una fecha específica.

    Args:
        fecha: Fecha en formato YYYY-MM-DD
        empleado_id: UUID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)
        tipo: ENTRADA o SALIDA (opcional)

    Returns:
        Lista de registros con datos del empleado
    """
```

**Query SQL:**
```sql
SELECT
    r.id,
    r.empleado_id,
    e.codigo_empleado,
    e.nombre || ' ' || e.apellido AS empleado_nombre,
    e.cargo,
    e.departamento,
    r.tipo_registro,
    r.punto_trabajo,
    r.fecha_registro,
    r.hora_registro,
    r.timestamp_registro,
    r.confianza_reconocimiento,
    r.observaciones
FROM registros r
JOIN empleados e ON r.empleado_id = e.id
WHERE r.fecha_registro = :fecha
  AND (:empleado_id IS NULL OR r.empleado_id = :empleado_id::uuid)
  AND (:restaurante IS NULL OR r.punto_trabajo = :restaurante)
  AND (:tipo IS NULL OR r.tipo_registro = :tipo)
ORDER BY r.hora_registro;
```

---

### 3. `consultar_registros_rango`

**Propósito:** Obtener registros en un rango de fechas.

```python
@mcp.tool()
async def consultar_registros_rango(
    fecha_inicio: str,
    fecha_fin: str,
    empleado_id: str = None,
    restaurante: str = None
) -> list[dict]:
    """
    Consulta registros en un rango de fechas.

    Args:
        fecha_inicio: Fecha inicio YYYY-MM-DD
        fecha_fin: Fecha fin YYYY-MM-DD
        empleado_id: UUID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)

    Returns:
        Lista de registros ordenados por fecha y hora
    """
```

**Query SQL:**
```sql
SELECT
    r.id,
    r.empleado_id,
    e.codigo_empleado,
    e.nombre || ' ' || e.apellido AS empleado_nombre,
    r.tipo_registro,
    r.punto_trabajo,
    r.fecha_registro,
    r.hora_registro,
    r.observaciones
FROM registros r
JOIN empleados e ON r.empleado_id = e.id
WHERE r.fecha_registro BETWEEN :fecha_inicio AND :fecha_fin
  AND (:empleado_id IS NULL OR r.empleado_id = :empleado_id::uuid)
  AND (:restaurante IS NULL OR r.punto_trabajo = :restaurante)
ORDER BY r.fecha_registro, r.hora_registro;
```

---

### 4. `calcular_horas_trabajadas_dia`

**Propósito:** Calcular horas trabajadas de un empleado en un día específico.

```python
@mcp.tool()
async def calcular_horas_trabajadas_dia(
    empleado_id: str,
    fecha: str
) -> dict:
    """
    Calcula las horas trabajadas de un empleado en una fecha.
    Empareja entradas con salidas y calcula intervalos.

    Args:
        empleado_id: UUID del empleado
        fecha: Fecha en formato YYYY-MM-DD

    Returns:
        {
            empleado_id, empleado_nombre, fecha,
            horas_trabajadas: float,
            horas_ordinarias: float,
            horas_extra_diurna: float,
            horas_extra_nocturna: float,
            horas_recargo_nocturno: float,
            registros: [{tipo, hora}, ...],
            intervalos: [{entrada, salida, horas}, ...],
            es_domingo: bool,
            es_festivo: bool,
            observaciones: str
        }
    """
```

**Query SQL (obtener registros):**
```sql
SELECT
    tipo_registro,
    hora_registro,
    observaciones
FROM registros
WHERE empleado_id = :empleado_id::uuid
  AND fecha_registro = :fecha
ORDER BY hora_registro;
```

**Lógica de cálculo:**
```python
def calcular_horas_dia(registros: list, fecha: date) -> dict:
    """
    Reglas laborales Colombia:
    - Jornada ordinaria: 8 horas/día
    - Hora extra diurna (6:00-21:00): +25% = factor 1.25
    - Hora extra nocturna (21:00-6:00): +75% = factor 1.75
    - Recargo nocturno (21:00-6:00): +35% sobre hora ordinaria
    - Dominical/Festivo: +75% = factor 1.75
    - Extra dominical diurna: +100% = factor 2.0
    - Extra dominical nocturna: +150% = factor 2.5
    """

    intervalos = []
    horas_total = 0

    # Emparejar ENTRADA con siguiente SALIDA
    i = 0
    while i < len(registros) - 1:
        if registros[i]['tipo_registro'] == 'ENTRADA':
            entrada = registros[i]['hora_registro']
            # Buscar siguiente SALIDA
            for j in range(i + 1, len(registros)):
                if registros[j]['tipo_registro'] == 'SALIDA':
                    salida = registros[j]['hora_registro']
                    horas = calcular_diferencia_horas(entrada, salida)
                    intervalos.append({
                        'entrada': str(entrada),
                        'salida': str(salida),
                        'horas': round(horas, 2)
                    })
                    horas_total += horas
                    i = j
                    break
        i += 1

    # Calcular tipos de horas
    horas_ordinarias = min(horas_total, 8)
    horas_extra = max(0, horas_total - 8)

    # Determinar si es nocturno (21:00 - 06:00)
    horas_nocturnas = calcular_horas_nocturnas(intervalos)
    horas_diurnas = horas_total - horas_nocturnas

    return {
        'horas_trabajadas': round(horas_total, 2),
        'horas_ordinarias': round(horas_ordinarias, 2),
        'horas_extra_diurna': round(max(0, horas_extra - horas_nocturnas), 2),
        'horas_extra_nocturna': round(min(horas_extra, horas_nocturnas), 2),
        'horas_recargo_nocturno': round(horas_nocturnas, 2),
        'intervalos': intervalos
    }
```

---

### 5. `reporte_horas_semanal`

**Propósito:** Reporte semanal de horas por empleado.

```python
@mcp.tool()
async def reporte_horas_semanal(
    empleado_id: str = None,
    fecha_semana: str = None,
    restaurante: str = None
) -> list[dict]:
    """
    Genera reporte semanal de horas trabajadas.
    Si no se especifica fecha, usa la semana actual.

    Args:
        empleado_id: UUID del empleado (opcional, todos si no se especifica)
        fecha_semana: Cualquier fecha de la semana YYYY-MM-DD (opcional)
        restaurante: Filtrar por restaurante (opcional)

    Returns:
        Lista por empleado con:
        {
            empleado_id, codigo, nombre,
            semana_inicio, semana_fin,
            dias: [{fecha, horas_trabajadas, ...}, ...],
            total_horas_semana: float,
            total_horas_ordinarias: float,
            total_horas_extra_diurna: float,
            total_horas_extra_nocturna: float,
            total_recargo_nocturno: float,
            total_dominical: float,
            alerta_exceso: bool,  # Si supera 48 horas
            horas_exceso: float
        }
    """
```

**Query SQL (registros de la semana):**
```sql
WITH semana AS (
    SELECT
        date_trunc('week', :fecha::date) AS inicio,
        date_trunc('week', :fecha::date) + INTERVAL '6 days' AS fin
)
SELECT
    r.empleado_id,
    e.codigo_empleado,
    e.nombre || ' ' || e.apellido AS empleado_nombre,
    e.liquida_dominical,
    e.dia_descanso,
    r.fecha_registro,
    r.tipo_registro,
    r.hora_registro,
    r.observaciones,
    EXTRACT(DOW FROM r.fecha_registro) AS dia_semana  -- 0=Domingo
FROM registros r
JOIN empleados e ON r.empleado_id = e.id
CROSS JOIN semana s
WHERE r.fecha_registro BETWEEN s.inicio AND s.fin
  AND (:empleado_id IS NULL OR r.empleado_id = :empleado_id::uuid)
  AND (:restaurante IS NULL OR r.punto_trabajo = :restaurante)
  AND e.activo = TRUE
ORDER BY e.apellido, e.nombre, r.fecha_registro, r.hora_registro;
```

---

### 6. `reporte_horas_mensual`

**Propósito:** Reporte mensual consolidado por empleado.

```python
@mcp.tool()
async def reporte_horas_mensual(
    anio: int,
    mes: int,
    empleado_id: str = None,
    restaurante: str = None
) -> list[dict]:
    """
    Genera reporte mensual de horas trabajadas.

    Args:
        anio: Año (ej: 2024)
        mes: Mes (1-12)
        empleado_id: UUID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)

    Returns:
        Lista por empleado con:
        {
            empleado_id, codigo, nombre, cargo, departamento,
            periodo: "Enero 2024",
            semanas: [{semana_num, horas, ...}, ...],
            resumen: {
                dias_trabajados: int,
                total_horas: float,
                horas_ordinarias: float,
                horas_extra_diurna: float,
                horas_extra_nocturna: float,
                recargo_nocturno: float,
                horas_dominical: float,
                horas_festivo: float
            },
            valor_estimado: {
                ordinarias: float,
                extra_diurna: float,
                extra_nocturna: float,
                recargo_nocturno: float,
                dominical: float,
                total: float
            }
        }
    """
```

**Query SQL:**
```sql
SELECT
    r.empleado_id,
    e.codigo_empleado,
    e.nombre,
    e.apellido,
    e.cargo,
    e.departamento,
    e.liquida_dominical,
    r.fecha_registro,
    r.tipo_registro,
    r.hora_registro,
    r.observaciones,
    EXTRACT(DOW FROM r.fecha_registro) AS dia_semana,
    EXTRACT(WEEK FROM r.fecha_registro) AS semana_num
FROM registros r
JOIN empleados e ON r.empleado_id = e.id
WHERE EXTRACT(YEAR FROM r.fecha_registro) = :anio
  AND EXTRACT(MONTH FROM r.fecha_registro) = :mes
  AND (:empleado_id IS NULL OR r.empleado_id = :empleado_id::uuid)
  AND (:restaurante IS NULL OR r.punto_trabajo = :restaurante)
  AND e.activo = TRUE
ORDER BY e.apellido, e.nombre, r.fecha_registro, r.hora_registro;
```

---

### 7. `obtener_ultimo_registro`

**Propósito:** Obtener el último registro de un empleado.

```python
@mcp.tool()
async def obtener_ultimo_registro(
    empleado_id: str
) -> dict:
    """
    Obtiene el último registro de un empleado.
    Útil para saber si debe registrar ENTRADA o SALIDA.

    Args:
        empleado_id: UUID del empleado

    Returns:
        {
            empleado_id, empleado_nombre,
            ultimo_registro: {tipo, fecha, hora, punto_trabajo},
            siguiente_accion: "ENTRADA" | "SALIDA"
        }
    """
```

**Query SQL:**
```sql
SELECT
    r.tipo_registro,
    r.fecha_registro,
    r.hora_registro,
    r.punto_trabajo,
    e.nombre || ' ' || e.apellido AS empleado_nombre
FROM registros r
JOIN empleados e ON r.empleado_id = e.id
WHERE r.empleado_id = :empleado_id::uuid
ORDER BY r.fecha_registro DESC, r.hora_registro DESC
LIMIT 1;
```

---

### 8. `estadisticas_asistencia`

**Propósito:** Estadísticas generales de asistencia.

```python
@mcp.tool()
async def estadisticas_asistencia(
    fecha_inicio: str,
    fecha_fin: str,
    restaurante: str = None
) -> dict:
    """
    Genera estadísticas de asistencia para un período.

    Args:
        fecha_inicio: Fecha inicio YYYY-MM-DD
        fecha_fin: Fecha fin YYYY-MM-DD
        restaurante: Filtrar por restaurante (opcional)

    Returns:
        {
            periodo: {inicio, fin, dias},
            totales: {
                empleados_unicos: int,
                total_registros: int,
                entradas: int,
                salidas: int,
                registros_forzados: int
            },
            por_restaurante: [{restaurante, registros, empleados}, ...],
            promedio_horas_dia: float,
            empleados_mas_horas: [{nombre, horas}, ...],
            dias_con_mas_registros: [{fecha, registros}, ...]
        }
    """
```

**Query SQL:**
```sql
SELECT
    COUNT(*) AS total_registros,
    COUNT(DISTINCT empleado_id) AS empleados_unicos,
    COUNT(*) FILTER (WHERE tipo_registro = 'ENTRADA') AS entradas,
    COUNT(*) FILTER (WHERE tipo_registro = 'SALIDA') AS salidas,
    COUNT(*) FILTER (WHERE observaciones LIKE '%FORZADO%') AS forzados,
    punto_trabajo
FROM registros
WHERE fecha_registro BETWEEN :fecha_inicio AND :fecha_fin
  AND (:restaurante IS NULL OR punto_trabajo = :restaurante)
GROUP BY punto_trabajo;
```

---

### 9. `empleados_sin_salida`

**Propósito:** Listar empleados con entrada pero sin salida registrada.

```python
@mcp.tool()
async def empleados_sin_salida(
    fecha: str = None
) -> list[dict]:
    """
    Lista empleados que tienen entrada pero no salida en una fecha.
    Si no se especifica fecha, usa la fecha actual.

    Args:
        fecha: Fecha YYYY-MM-DD (opcional, default: hoy)

    Returns:
        Lista de empleados pendientes con:
        {
            empleado_id, codigo, nombre,
            hora_entrada, punto_trabajo,
            horas_transcurridas: float
        }
    """
```

**Query SQL:**
```sql
WITH entradas AS (
    SELECT
        empleado_id,
        MIN(hora_registro) AS primera_entrada,
        punto_trabajo
    FROM registros
    WHERE fecha_registro = :fecha
      AND tipo_registro = 'ENTRADA'
    GROUP BY empleado_id, punto_trabajo
),
salidas AS (
    SELECT DISTINCT empleado_id
    FROM registros
    WHERE fecha_registro = :fecha
      AND tipo_registro = 'SALIDA'
)
SELECT
    e.id AS empleado_id,
    e.codigo_empleado,
    e.nombre || ' ' || e.apellido AS empleado_nombre,
    en.primera_entrada AS hora_entrada,
    en.punto_trabajo,
    EXTRACT(EPOCH FROM (NOW() - ((:fecha)::date + en.primera_entrada))) / 3600 AS horas_transcurridas
FROM entradas en
JOIN empleados e ON en.empleado_id = e.id
LEFT JOIN salidas s ON en.empleado_id = s.empleado_id
WHERE s.empleado_id IS NULL
ORDER BY en.primera_entrada;
```

---

### 10. `obtener_configuracion`

**Propósito:** Obtener configuraciones del sistema para cálculos.

```python
@mcp.tool()
async def obtener_configuracion(
    clave: str = None
) -> dict | list[dict]:
    """
    Obtiene configuraciones del sistema.
    Si no se especifica clave, retorna todas.

    Args:
        clave: Nombre de la configuración (opcional)

    Returns:
        Configuración o lista de configuraciones
    """
```

**Query SQL:**
```sql
SELECT clave, valor, descripcion, tipo_dato
FROM configuracion
WHERE (:clave IS NULL OR clave = :clave)
ORDER BY clave;
```

**Configuraciones relevantes para nómina:**
| Clave | Descripción | Tipo |
|-------|-------------|------|
| `horas_semanales` | Límite horas semanales (48) | integer |
| `max_horas_por_dia` | Máximo horas/día (10) | integer |
| `valor_hora_ordinaria` | Valor hora normal | decimal |
| `valor_hora_extra_diurna` | Valor extra diurna (+25%) | decimal |
| `valor_hora_extra_nocturna` | Valor extra nocturna (+75%) | decimal |
| `autoclose_forced_exit_time_1` | Hora cierre forzado turno 1 | string |
| `autoclose_forced_exit_time_2` | Hora cierre forzado turno 2 | string |

---

### 11. `buscar_empleado`

**Propósito:** Buscar empleado por código o nombre.

```python
@mcp.tool()
async def buscar_empleado(
    termino: str
) -> list[dict]:
    """
    Busca empleados por código, nombre o apellido.

    Args:
        termino: Texto a buscar (código, nombre o apellido)

    Returns:
        Lista de empleados que coinciden
    """
```

**Query SQL:**
```sql
SELECT
    id,
    codigo_empleado,
    nombre,
    apellido,
    cargo,
    departamento,
    punto_trabajo,
    activo
FROM empleados
WHERE codigo_empleado ILIKE '%' || :termino || '%'
   OR nombre ILIKE '%' || :termino || '%'
   OR apellido ILIKE '%' || :termino || '%'
ORDER BY
    CASE WHEN codigo_empleado ILIKE :termino THEN 0 ELSE 1 END,
    apellido, nombre
LIMIT 20;
```

---

### 12. `resumen_nomina_quincenal`

**Propósito:** Resumen para liquidación de nómina quincenal.

```python
@mcp.tool()
async def resumen_nomina_quincenal(
    anio: int,
    mes: int,
    quincena: int,  # 1 = días 1-15, 2 = días 16-fin
    restaurante: str = None
) -> list[dict]:
    """
    Genera resumen de nómina para una quincena.

    Args:
        anio: Año
        mes: Mes (1-12)
        quincena: 1 (días 1-15) o 2 (días 16-fin de mes)
        restaurante: Filtrar por restaurante (opcional)

    Returns:
        Lista por empleado con:
        {
            empleado_id, codigo, nombre, cargo,
            dias_trabajados,
            horas: {
                ordinarias, extra_diurna, extra_nocturna,
                recargo_nocturno, dominical, festivo
            },
            valores: {
                ordinarias, extra_diurna, extra_nocturna,
                recargo_nocturno, dominical, festivo,
                subtotal, deducciones, total
            },
            detalle_dias: [{fecha, entrada, salida, horas}, ...]
        }
    """
```

---

## Implementación del Servidor MCP

### Estructura del Proyecto

```
mcp-reportes-acceso/
├── src/
│   └── mcp_reportes/
│       ├── __init__.py
│       ├── server.py           # Servidor MCP principal
│       ├── database.py         # Conexión PostgreSQL
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── empleados.py    # consultar_empleados, buscar_empleado
│       │   ├── registros.py    # consultar_registros_*
│       │   ├── reportes.py     # reporte_horas_*, estadisticas
│       │   └── nomina.py       # resumen_nomina_quincenal
│       └── utils/
│           ├── __init__.py
│           ├── calculos.py     # Lógica de cálculo de horas
│           └── fechas.py       # Utilidades de fechas
├── pyproject.toml
├── README.md
└── .env
```

### Código del Servidor

```python
# src/mcp_reportes/server.py
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import json

from .database import Database
from .tools import empleados, registros, reportes, nomina

# Crear servidor MCP
server = Server("mcp-reportes-acceso")

# Instancia de base de datos
db = Database()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lista todas las herramientas disponibles"""
    return [
        Tool(
            name="consultar_empleados",
            description="Lista empleados del sistema con filtros opcionales por restaurante y departamento",
            inputSchema={
                "type": "object",
                "properties": {
                    "activos_solo": {"type": "boolean", "default": True},
                    "restaurante": {"type": "string", "enum": ["Bandidos", "Sumo", "Leños y Parrilla"]},
                    "departamento": {"type": "string"}
                }
            }
        ),
        Tool(
            name="buscar_empleado",
            description="Busca empleados por código, nombre o apellido",
            inputSchema={
                "type": "object",
                "properties": {
                    "termino": {"type": "string", "description": "Texto a buscar"}
                },
                "required": ["termino"]
            }
        ),
        Tool(
            name="consultar_registros_fecha",
            description="Consulta registros de entrada/salida de una fecha específica",
            inputSchema={
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "format": "date"},
                    "empleado_id": {"type": "string", "format": "uuid"},
                    "restaurante": {"type": "string"},
                    "tipo": {"type": "string", "enum": ["ENTRADA", "SALIDA"]}
                },
                "required": ["fecha"]
            }
        ),
        Tool(
            name="consultar_registros_rango",
            description="Consulta registros en un rango de fechas",
            inputSchema={
                "type": "object",
                "properties": {
                    "fecha_inicio": {"type": "string", "format": "date"},
                    "fecha_fin": {"type": "string", "format": "date"},
                    "empleado_id": {"type": "string", "format": "uuid"},
                    "restaurante": {"type": "string"}
                },
                "required": ["fecha_inicio", "fecha_fin"]
            }
        ),
        Tool(
            name="calcular_horas_trabajadas_dia",
            description="Calcula horas trabajadas de un empleado en un día específico con desglose de extras",
            inputSchema={
                "type": "object",
                "properties": {
                    "empleado_id": {"type": "string", "format": "uuid"},
                    "fecha": {"type": "string", "format": "date"}
                },
                "required": ["empleado_id", "fecha"]
            }
        ),
        Tool(
            name="reporte_horas_semanal",
            description="Genera reporte semanal de horas trabajadas por empleado con alertas de exceso",
            inputSchema={
                "type": "object",
                "properties": {
                    "empleado_id": {"type": "string", "format": "uuid"},
                    "fecha_semana": {"type": "string", "format": "date"},
                    "restaurante": {"type": "string"}
                }
            }
        ),
        Tool(
            name="reporte_horas_mensual",
            description="Genera reporte mensual consolidado de horas y valores por empleado",
            inputSchema={
                "type": "object",
                "properties": {
                    "anio": {"type": "integer"},
                    "mes": {"type": "integer", "minimum": 1, "maximum": 12},
                    "empleado_id": {"type": "string", "format": "uuid"},
                    "restaurante": {"type": "string"}
                },
                "required": ["anio", "mes"]
            }
        ),
        Tool(
            name="obtener_ultimo_registro",
            description="Obtiene el último registro de un empleado para saber si debe marcar entrada o salida",
            inputSchema={
                "type": "object",
                "properties": {
                    "empleado_id": {"type": "string", "format": "uuid"}
                },
                "required": ["empleado_id"]
            }
        ),
        Tool(
            name="estadisticas_asistencia",
            description="Genera estadísticas generales de asistencia para un período",
            inputSchema={
                "type": "object",
                "properties": {
                    "fecha_inicio": {"type": "string", "format": "date"},
                    "fecha_fin": {"type": "string", "format": "date"},
                    "restaurante": {"type": "string"}
                },
                "required": ["fecha_inicio", "fecha_fin"]
            }
        ),
        Tool(
            name="empleados_sin_salida",
            description="Lista empleados con entrada pero sin salida registrada en una fecha",
            inputSchema={
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "format": "date"}
                }
            }
        ),
        Tool(
            name="obtener_configuracion",
            description="Obtiene configuraciones del sistema para cálculos de nómina",
            inputSchema={
                "type": "object",
                "properties": {
                    "clave": {"type": "string"}
                }
            }
        ),
        Tool(
            name="resumen_nomina_quincenal",
            description="Genera resumen para liquidación de nómina quincenal",
            inputSchema={
                "type": "object",
                "properties": {
                    "anio": {"type": "integer"},
                    "mes": {"type": "integer", "minimum": 1, "maximum": 12},
                    "quincena": {"type": "integer", "enum": [1, 2]},
                    "restaurante": {"type": "string"}
                },
                "required": ["anio", "mes", "quincena"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Ejecuta la herramienta solicitada"""

    try:
        if name == "consultar_empleados":
            result = await empleados.consultar_empleados(db, **arguments)
        elif name == "buscar_empleado":
            result = await empleados.buscar_empleado(db, **arguments)
        elif name == "consultar_registros_fecha":
            result = await registros.consultar_registros_fecha(db, **arguments)
        elif name == "consultar_registros_rango":
            result = await registros.consultar_registros_rango(db, **arguments)
        elif name == "calcular_horas_trabajadas_dia":
            result = await reportes.calcular_horas_trabajadas_dia(db, **arguments)
        elif name == "reporte_horas_semanal":
            result = await reportes.reporte_horas_semanal(db, **arguments)
        elif name == "reporte_horas_mensual":
            result = await reportes.reporte_horas_mensual(db, **arguments)
        elif name == "obtener_ultimo_registro":
            result = await registros.obtener_ultimo_registro(db, **arguments)
        elif name == "estadisticas_asistencia":
            result = await reportes.estadisticas_asistencia(db, **arguments)
        elif name == "empleados_sin_salida":
            result = await registros.empleados_sin_salida(db, **arguments)
        elif name == "obtener_configuracion":
            result = await reportes.obtener_configuracion(db, **arguments)
        elif name == "resumen_nomina_quincenal":
            result = await nomina.resumen_nomina_quincenal(db, **arguments)
        else:
            result = {"error": f"Herramienta '{name}' no encontrada"}

        return [TextContent(type="text", text=json.dumps(result, default=str, ensure_ascii=False, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def main():
    """Punto de entrada principal"""
    await db.connect()

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
```

### Módulo de Base de Datos

```python
# src/mcp_reportes/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        # Usar DATABASE_URL_ASYNC si está disponible, sino DATABASE_URL_FALLBACK
        self.database_url = os.getenv(
            "DATABASE_URL_ASYNC",
            os.getenv(
                "DATABASE_URL_FALLBACK",
                "postgresql+asyncpg://cocson:Ia$10018084@coson-prod_control_acceso_coson:5432/acceso-cocson"
            )
        )
        self.engine = None
        self.session_factory = None

    async def connect(self):
        """Establece conexión con la base de datos"""
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_size=5,
            max_overflow=10
        )
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def disconnect(self):
        """Cierra la conexión"""
        if self.engine:
            await self.engine.dispose()

    async def execute(self, query: str, params: dict = None) -> list[dict]:
        """Ejecuta una consulta y retorna resultados como lista de dicts"""
        async with self.session_factory() as session:
            result = await session.execute(text(query), params or {})
            rows = result.fetchall()
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]

    async def execute_one(self, query: str, params: dict = None) -> dict | None:
        """Ejecuta una consulta y retorna un solo resultado"""
        results = await self.execute(query, params)
        return results[0] if results else None
```

### Utilidades de Cálculo

```python
# src/mcp_reportes/utils/calculos.py
from datetime import datetime, time, date, timedelta
from typing import List, Dict

# Constantes laborales Colombia
HORA_INICIO_NOCTURNO = time(21, 0)  # 9:00 PM
HORA_FIN_NOCTURNO = time(6, 0)      # 6:00 AM
JORNADA_ORDINARIA = 8               # horas
LIMITE_SEMANAL = 48                 # horas

# Factores de recargo
FACTOR_EXTRA_DIURNA = 1.25          # +25%
FACTOR_EXTRA_NOCTURNA = 1.75        # +75%
FACTOR_RECARGO_NOCTURNO = 0.35      # +35%
FACTOR_DOMINICAL = 1.75             # +75%
FACTOR_EXTRA_DOMINICAL_DIURNA = 2.0    # +100%
FACTOR_EXTRA_DOMINICAL_NOCTURNA = 2.5  # +150%


def es_hora_nocturna(hora: time) -> bool:
    """Determina si una hora está en franja nocturna (21:00 - 06:00)"""
    return hora >= HORA_INICIO_NOCTURNO or hora < HORA_FIN_NOCTURNO


def calcular_diferencia_horas(inicio: time, fin: time) -> float:
    """Calcula diferencia en horas entre dos tiempos"""
    inicio_dt = datetime.combine(date.today(), inicio)
    fin_dt = datetime.combine(date.today(), fin)

    # Si fin es menor que inicio, asumimos que cruzó medianoche
    if fin < inicio:
        fin_dt += timedelta(days=1)

    diferencia = (fin_dt - inicio_dt).total_seconds() / 3600
    return round(diferencia, 2)


def calcular_horas_nocturnas(entrada: time, salida: time) -> float:
    """Calcula cuántas horas de un intervalo son nocturnas"""
    total_nocturnas = 0.0

    # Convertir a minutos desde medianoche para facilitar cálculos
    entrada_min = entrada.hour * 60 + entrada.minute
    salida_min = salida.hour * 60 + salida.minute

    # Si cruzó medianoche
    if salida_min < entrada_min:
        salida_min += 24 * 60

    # Franja nocturna: 21:00 (1260 min) a 06:00 (360 min + 1440 = 1800 min del día siguiente)
    nocturno_inicio = 21 * 60  # 1260
    nocturno_fin = 6 * 60      # 360

    for minuto in range(entrada_min, salida_min):
        minuto_normalizado = minuto % (24 * 60)
        if minuto_normalizado >= nocturno_inicio or minuto_normalizado < nocturno_fin:
            total_nocturnas += 1/60

    return round(total_nocturnas, 2)


def calcular_horas_dia(registros: List[Dict], fecha: date) -> Dict:
    """
    Calcula todas las horas de un día con desglose completo.

    Args:
        registros: Lista de registros ordenados por hora
        fecha: Fecha del cálculo

    Returns:
        Diccionario con desglose de horas
    """
    intervalos = []
    horas_total = 0.0
    horas_nocturnas_total = 0.0

    # Determinar si es domingo (0) o festivo
    es_domingo = fecha.weekday() == 6

    # Emparejar ENTRADA con siguiente SALIDA
    i = 0
    while i < len(registros):
        if registros[i]['tipo_registro'] == 'ENTRADA':
            entrada = registros[i]['hora_registro']

            # Buscar siguiente SALIDA
            for j in range(i + 1, len(registros)):
                if registros[j]['tipo_registro'] == 'SALIDA':
                    salida = registros[j]['hora_registro']

                    horas = calcular_diferencia_horas(entrada, salida)
                    horas_nocturnas = calcular_horas_nocturnas(entrada, salida)

                    intervalos.append({
                        'entrada': str(entrada),
                        'salida': str(salida),
                        'horas': horas,
                        'horas_nocturnas': horas_nocturnas,
                        'horas_diurnas': round(horas - horas_nocturnas, 2)
                    })

                    horas_total += horas
                    horas_nocturnas_total += horas_nocturnas
                    i = j
                    break
        i += 1

    # Calcular desglose
    horas_diurnas_total = round(horas_total - horas_nocturnas_total, 2)

    # Horas ordinarias vs extras
    horas_ordinarias = min(horas_total, JORNADA_ORDINARIA)
    horas_extra = max(0, horas_total - JORNADA_ORDINARIA)

    # Distribuir extras entre diurnas y nocturnas
    if horas_extra > 0:
        proporcion_nocturna = horas_nocturnas_total / horas_total if horas_total > 0 else 0
        horas_extra_nocturna = round(horas_extra * proporcion_nocturna, 2)
        horas_extra_diurna = round(horas_extra - horas_extra_nocturna, 2)
    else:
        horas_extra_diurna = 0
        horas_extra_nocturna = 0

    return {
        'fecha': str(fecha),
        'es_domingo': es_domingo,
        'horas_trabajadas': round(horas_total, 2),
        'horas_ordinarias': round(horas_ordinarias, 2),
        'horas_extra_diurna': horas_extra_diurna,
        'horas_extra_nocturna': horas_extra_nocturna,
        'horas_recargo_nocturno': round(horas_nocturnas_total, 2),
        'horas_dominical': round(horas_total, 2) if es_domingo else 0,
        'intervalos': intervalos,
        'total_intervalos': len(intervalos)
    }


def calcular_valor_horas(horas: Dict, config: Dict) -> Dict:
    """
    Calcula el valor monetario de las horas trabajadas.

    Args:
        horas: Diccionario con desglose de horas
        config: Configuración con valores hora

    Returns:
        Diccionario con valores calculados
    """
    valor_ordinaria = float(config.get('valor_hora_ordinaria', 5833.33))
    valor_extra_diurna = float(config.get('valor_hora_extra_diurna', valor_ordinaria * FACTOR_EXTRA_DIURNA))
    valor_extra_nocturna = float(config.get('valor_hora_extra_nocturna', valor_ordinaria * FACTOR_EXTRA_NOCTURNA))

    valores = {
        'ordinarias': round(horas['horas_ordinarias'] * valor_ordinaria, 2),
        'extra_diurna': round(horas['horas_extra_diurna'] * valor_extra_diurna, 2),
        'extra_nocturna': round(horas['horas_extra_nocturna'] * valor_extra_nocturna, 2),
        'recargo_nocturno': round(horas['horas_recargo_nocturno'] * valor_ordinaria * FACTOR_RECARGO_NOCTURNO, 2),
    }

    if horas.get('es_domingo'):
        valores['dominical'] = round(horas['horas_dominical'] * valor_ordinaria * FACTOR_DOMINICAL, 2)
    else:
        valores['dominical'] = 0

    valores['total'] = sum(valores.values())

    return valores
```

---

## Configuración para Claude Desktop

```json
{
  "mcpServers": {
    "reportes-acceso": {
      "command": "python",
      "args": ["-m", "mcp_reportes.server"],
      "cwd": "/ruta/al/proyecto/mcp-reportes-acceso",
      "env": {
        "DATABASE_URL_ASYNC": "postgresql+asyncpg://cocson:Ia$10018084@coson-prod_control_acceso_coson:5432/acceso-cocson",
        "TIMEZONE": "America/Bogota"
      }
    }
  }
}
```

---

## Ejemplos de Uso

### Consultar horas de un empleado en una semana

```
Usuario: ¿Cuántas horas trabajó Juan Pérez la semana pasada?

Claude: [Usa buscar_empleado con termino="Juan Pérez"]
        [Usa reporte_horas_semanal con empleado_id y fecha de la semana pasada]

        Juan Pérez trabajó 45 horas la semana del 6 al 12 de enero:
        - Lunes: 8h (8:00 - 17:00)
        - Martes: 9h (7:30 - 17:30) - 1h extra diurna
        - Miércoles: 8h
        - Jueves: 10h (7:00 - 18:00) - 2h extra diurna
        - Viernes: 8h
        - Sábado: 2h (10:00 - 12:00)

        Resumen:
        - Horas ordinarias: 40h
        - Horas extra diurna: 5h
        - Total: 45h (dentro del límite de 48h semanales)
```

### Reporte mensual para nómina

```
Usuario: Necesito el reporte de enero 2024 para liquidar nómina del restaurante Bandidos

Claude: [Usa reporte_horas_mensual con anio=2024, mes=1, restaurante="Bandidos"]

        Reporte de Enero 2024 - Bandidos:

        | Empleado | Días | H.Ord | H.Ex.D | H.Ex.N | Rec.Noc | Dom | Total |
        |----------|------|-------|--------|--------|---------|-----|-------|
        | Juan P.  | 22   | 176h  | 12h    | 4h     | 8h      | 8h  | 200h  |
        | María G. | 20   | 160h  | 8h     | 0h     | 0h      | 0h  | 168h  |
        ...
```

---

## Notas Importantes

1. **Zona horaria:** El sistema usa hora de Colombia (UTC-5). Las consultas asumen esta zona.

2. **Registros forzados:** Los registros con `[FORZADO]` en observaciones fueron creados por el autocierre automático.

3. **Dominicales:** Solo se calculan para empleados con `liquida_dominical = true`.

4. **Límites:** El sistema alerta cuando un empleado supera 48 horas semanales.

5. **Festivos:** Para calcular festivos colombianos, implementar lógica adicional o consultar tabla de festivos.

---

*Documento para implementación de servidor MCP - Reportes de Control de Acceso v2.0*
