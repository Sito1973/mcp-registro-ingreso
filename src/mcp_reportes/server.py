"""Servidor MCP para Reportes de Control de Acceso con SSE"""

import asyncio
import os
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn

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
                    "activos_solo": {"type": "boolean", "default": True, "description": "Solo empleados activos"},
                    "restaurante": {"type": "string", "description": "Filtrar por restaurante"},
                    "departamento": {"type": "string", "description": "Filtrar por departamento"}
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
                    "empleado_id": {"type": "string"},
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
                    "empleado_id": {"type": "string"},
                    "restaurante": {"type": "string"}
                },
                "required": ["fecha_inicio", "fecha_fin"]
            }
        ),
        Tool(
            name="calcular_horas_trabajadas_dia",
            description="Calcula horas trabajadas de un empleado en un día con desglose de extras",
            inputSchema={
                "type": "object",
                "properties": {
                    "empleado_id": {"type": "string"},
                    "fecha": {"type": "string", "format": "date"}
                },
                "required": ["empleado_id", "fecha"]
            }
        ),
        Tool(
            name="reporte_horas_semanal",
            description="Genera reporte semanal de horas trabajadas por empleado",
            inputSchema={
                "type": "object",
                "properties": {
                    "empleado_id": {"type": "string"},
                    "fecha_semana": {"type": "string", "format": "date"},
                    "restaurante": {"type": "string"}
                }
            }
        ),
        Tool(
            name="reporte_horas_mensual",
            description="Genera reporte mensual consolidado de horas por empleado",
            inputSchema={
                "type": "object",
                "properties": {
                    "anio": {"type": "integer"},
                    "mes": {"type": "integer", "minimum": 1, "maximum": 12},
                    "empleado_id": {"type": "string"},
                    "restaurante": {"type": "string"}
                },
                "required": ["anio", "mes"]
            }
        ),
        Tool(
            name="obtener_ultimo_registro",
            description="Obtiene el último registro de un empleado",
            inputSchema={
                "type": "object",
                "properties": {
                    "empleado_id": {"type": "string"}
                },
                "required": ["empleado_id"]
            }
        ),
        Tool(
            name="estadisticas_asistencia",
            description="Genera estadísticas de asistencia para un período",
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
            description="Lista empleados con entrada pero sin salida en una fecha",
            inputSchema={
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "format": "date"}
                }
            }
        ),
        Tool(
            name="obtener_configuracion",
            description="Obtiene configuraciones del sistema para nómina",
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


# === SSE Transport ===

# Diccionario para manejar sesiones SSE
sse_sessions = {}


async def handle_sse(scope, receive, send):
    """Maneja conexiones SSE (función ASGI raw)"""
    sse = SseServerTransport("/messages")

    async with sse.connect_sse(scope, receive, send) as streams:
        await server.run(
            streams[0],
            streams[1],
            server.create_initialization_options()
        )


async def handle_messages(scope, receive, send):
    """Maneja mensajes POST del cliente (función ASGI raw)"""
    sse = SseServerTransport("/messages")
    await sse.handle_post_message(scope, receive, send)


async def health_check(request):
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "server": "mcp-reportes-acceso",
        "version": "1.0.0"
    })


# Crear app Starlette
app = Starlette(
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Mount("/sse", app=handle_sse),
        Mount("/messages", app=handle_messages),
    ],
    on_startup=[lambda: asyncio.create_task(db.connect())],
    on_shutdown=[lambda: asyncio.create_task(db.disconnect())]
)


async def run_stdio():
    """Ejecuta el servidor en modo stdio (para Claude Desktop)"""
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


def main():
    """Punto de entrada principal"""
    port = int(os.getenv("PORT", "8000"))
    
    if os.getenv("PORT"):
        print(f"🚀 Iniciando servidor MCP en modo SSE (puerto {port})")
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        print("🚀 Iniciando servidor MCP en modo stdio")
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
