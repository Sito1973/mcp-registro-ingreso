# 🛠️ Technical Changelog - SSE & Database Fixes (Branch: `sse-stable`)

Este documento detalla las modificaciones técnicas críticas aplicadas para estabilizar el despliegue del servidor MCP en Easypanel, solucionando problemas de concurrencia ASGI, inferencia de tipos SQL y manejo de fechas en `asyncpg`.

---

## 1. ⚡ SSE Transport Fix (ASGI Concurrency)

**Problema:**
La aplicación lanzaba un `RuntimeError: Unexpected ASGI message 'http.response.start'` y `TypeError: 'NoneType' object is not callable` al usar los endpoints SSE.
Esto ocurría porque tanto la librería interna `mcp` como `Starlette` intentaban enviar una respuesta HTTP al cliente, causando una condición de carrera o respuestas duplicadas. Además, los handlers retornaban `None` implícitamente al cerrar la conexión.

**Solución (`server.py`):**
Se implementó una clase `NoOpResponse` que satisface el contrato de Starlette (retornar un objeto `Response`) pero no realiza ninguna acción de red (`send`), delegando el control total del socket a la librería `mcp`.

```python
class NoOpResponse(Response):
    """Respuesta silenciosa para evitar doble envío ASGI."""
    async def __call__(self, scope, receive, send):
        return  # No hace nada, cede el control

async def handle_sse(request):
    # ... lógica de conexión ...
    return NoOpResponse()  # Fix: Retorna objeto válido
```

---

## 2. 🛡️ SQL Type Casting (Ambiguous Parameters)

**Problema:**
`asyncpg` lanzaba `AmbiguousParameterError` (error `P300`) cuando los parámetros opcionales (bind vars) eran `NULL` (None en Python). PostgreSQL no podía inferir el tipo de dato del parámetro `$1` si este era nulo.
El uso de la sintaxis abreviada de PostgreSQL `::type` (ej: `:param::text`) causaba conflictos de parsing con `SQLAlchemy.text()`.

**Solución (Todos los archivos en `tools/`):**
Se reemplazó la sintaxis `::type` por el estándar SQL explícito `CAST(:param AS type)`. Esto asegura que PostgreSQL reciba el tipo correcto incluso si el valor es `NULL`.

**Antes (Problemático):**
```sql
WHERE (:restaurante::text IS NULL OR punto_trabajo = :restaurante)
```

**Después (Corregido):**
```sql
WHERE (CAST(:restaurante AS text) IS NULL OR punto_trabajo = :restaurante)
```

---

## 3. 📅 Date Object Handling (Asyncpg DataError)

**Problema:**
Se observó `DataError: invalid input for query argument` porque se pasaban cadenas de texto (`str`) en formato `'YYYY-MM-DD'` a parámetros SQL esperados como `DATE`. A diferencia de `psycopg2`, `asyncpg` es estricto con los tipos y no realiza conversión automática de strings a fechas.

**Solución (`registros.py`, `reportes.py`, `nomina.py`):**
Se refactorizó la capa de herramientas para asegurar que todas las fechas sean convertidas a objetos `datetime.date` antes de ser pasadas al método `db.execute()`. Se aseguró que el import `from datetime import datetime` esté a nivel de módulo para evitar errores de `NameError` en consultas de rango.

```python
# Antes
params = {'fecha': "2026-01-02"} 

# Después
from datetime import datetime
params = {'fecha': datetime.strptime("2026-01-02", "%Y-%m-%d").date()}
```

---

## Resumen de Archivos Afectados

| Archivo | Cambio Principal |
| :--- | :--- |
| `src/mcp_reportes/server.py` | Implementación de `NoOpResponse` en endpoints SSE. |
| `src/mcp_reportes/tools/empleados.py` | **SQL CAST:** `CAST(:activo AS boolean)`, etc. |
| `src/mcp_reportes/tools/registros.py` | **SQL CAST** y conversión `str` -> `date`. |
| `src/mcp_reportes/tools/reportes.py` | Conversión estricta de objetos `date` en reportes semanales/mensuales. |
| `src/mcp_reportes/tools/nomina.py` | Eliminación de `str()` redundante en rangos de fechas. |

---

## 🔍 4. Robustez en Filtrado (ILIKE + Comodines)

**Problema:**
Se detectaron inconsistencias en los nombres de los puntos de trabajo (restaurantes) entre las tablas (ej: `'Leños y Parrilla'` vs `'Leños Y Parrila'`). El uso de igualdad estricta (`=`) causaba que las consultas devolvieran 0 resultados si el filtro no coincidía exactamente con el typo en la base de datos.

**Solución:**
Se actualizaron todas las consultas SQL cambiándo `=` por `ILIKE` con comodines `%`:
```sql
AND punto_trabajo ILIKE '%' || :restaurante || '%'
```
Esto permite que filtros como "Leños" o "Parrilla" funcionen correctamente a pesar de variaciones en mayúsculas, tildes o errores tipográficos menores.

