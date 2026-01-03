# MCP Reportes de Control de Acceso

Servidor MCP (Model Context Protocol) para consultar reportes de nómina y asistencia desde el sistema de Control de Acceso con Reconocimiento Facial.

## Características

- 12 herramientas MCP para consultas de empleados, registros y reportes
- Conexión async a PostgreSQL via asyncpg
- Cálculos automáticos de horas extras según normativa colombiana
- Soporte SSE para despliegue en Easypanel

## Herramientas Disponibles

| Herramienta | Descripción |
|-------------|-------------|
| `consultar_empleados` | Lista empleados con filtros |
| `buscar_empleado` | Busca por código/nombre |
| `consultar_registros_fecha` | Registros de una fecha |
| `consultar_registros_rango` | Registros en rango |
| `calcular_horas_trabajadas_dia` | Horas de un día con desglose |
| `reporte_horas_semanal` | Reporte semanal |
| `reporte_horas_mensual` | Consolidado mensual |
| `obtener_ultimo_registro` | Último registro de empleado |
| `estadisticas_asistencia` | Estadísticas generales |
| `empleados_sin_salida` | Empleados sin salida |
| `obtener_configuracion` | Configuraciones del sistema |
| `resumen_nomina_quincenal` | Resumen para nómina |

## Instalación Local

```bash
pip install -e .
python -m mcp_reportes.server
```

## Despliegue en Easypanel

1. Push código a GitHub
2. En Easypanel: crear App → seleccionar repo → Deploy
3. Configurar variables de entorno:
   - `DATABASE_URL_ASYNC`: URL de PostgreSQL
   - `TIMEZONE`: `America/Bogota`
   - `PORT`: `8000`

## Configuración Claude Desktop

```json
{
  "mcpServers": {
    "reportes-acceso": {
      "command": "python",
      "args": ["-m", "mcp_reportes.server"],
      "cwd": "/ruta/al/proyecto",
      "env": {
        "DATABASE_URL_ASYNC": "postgresql+asyncpg://user:pass@host:5432/db",
        "TIMEZONE": "America/Bogota"
      }
    }
  }
}
```

## Uso con SSE (Easypanel)

El servidor expone un endpoint SSE en `http://host:8000/sse` para comunicación con clientes MCP remotos.
