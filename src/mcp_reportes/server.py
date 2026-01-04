"""Servidor MCP para Reportes de Control de Acceso con soporte SSE para Easypanel"""

import asyncio
import os
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route
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
                    "restaurante": {"type": "string", "enum": ["Bandidos", "Sumo", "Leños y Parrilla"], "description": "Filtrar por restaurante"},
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
                    "termino": {"type": "string", "description": "Texto a buscar (código, nombre o apellido)"}
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
                    "fecha": {"type": "string", "format": "date", "description": "Fecha en formato YYYY-MM-DD"},
                    "empleado_id": {"type": "string", "format": "uuid", "description": "UUID del empleado"},
                    "restaurante": {"type": "string", "description": "Filtrar por restaurante"},
                    "tipo": {"type": "string", "enum": ["ENTRADA", "SALIDA"], "description": "Tipo de registro"}
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
                    "fecha_inicio": {"type": "string", "format": "date", "description": "Fecha inicio YYYY-MM-DD"},
                    "fecha_fin": {"type": "string", "format": "date", "description": "Fecha fin YYYY-MM-DD"},
                    "empleado_id": {"type": "string", "format": "uuid", "description": "UUID del empleado"},
                    "restaurante": {"type": "string", "description": "Filtrar por restaurante"}
                },
                "required": ["fecha_inicio", "fecha_fin"]
            }
        ),
        Tool(
            name="calcular_horas_trabajadas_dia",
            description="Calcula horas trabajadas de un empleado en un día específico con desglose de extras y recargos",
            inputSchema={
                "type": "object",
                "properties": {
                    "empleado_id": {"type": "string", "format": "uuid", "description": "UUID del empleado"},
                    "fecha": {"type": "string", "format": "date", "description": "Fecha YYYY-MM-DD"}
                },
                "required": ["empleado_id", "fecha"]
            }
        ),
        Tool(
            name="reporte_horas_semanal",
            description="Genera reporte semanal de horas trabajadas por empleado con alertas de exceso (>48h)",
            inputSchema={
                "type": "object",
                "properties": {
                    "empleado_id": {"type": "string", "format": "uuid", "description": "UUID del empleado (opcional, todos si no se especifica)"},
                    "fecha_semana": {"type": "string", "format": "date", "description": "Cualquier fecha de la semana YYYY-MM-DD"},
                    "restaurante": {"type": "string", "description": "Filtrar por restaurante"}
                }
            }
        ),
        Tool(
            name="reporte_horas_mensual",
            description="Genera reporte mensual consolidado de horas y valores por empleado",
            inputSchema={
                "type": "object",
                "properties": {
                    "anio": {"type": "integer", "description": "Año (ej: 2024)"},
                    "mes": {"type": "integer", "minimum": 1, "maximum": 12, "description": "Mes (1-12)"},
                    "empleado_id": {"type": "string", "format": "uuid", "description": "UUID del empleado"},
                    "restaurante": {"type": "string", "description": "Filtrar por restaurante"}
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
                    "empleado_id": {"type": "string", "format": "uuid", "description": "UUID del empleado"}
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
                    "fecha_inicio": {"type": "string", "format": "date", "description": "Fecha inicio YYYY-MM-DD"},
                    "fecha_fin": {"type": "string", "format": "date", "description": "Fecha fin YYYY-MM-DD"},
                    "restaurante": {"type": "string", "description": "Filtrar por restaurante"}
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
                    "fecha": {"type": "string", "format": "date", "description": "Fecha YYYY-MM-DD (default: hoy)"}
                }
            }
        ),
        Tool(
            name="obtener_configuracion",
            description="Obtiene configuraciones del sistema para cálculos de nómina (valores hora, límites, etc)",
            inputSchema={
                "type": "object",
                "properties": {
                    "clave": {"type": "string", "description": "Nombre de la configuración (opcional, todas si no se especifica)"}
                }
            }
        ),
        Tool(
            name="resumen_nomina_quincenal",
            description="Genera resumen para liquidación de nómina quincenal con horas y valores",
            inputSchema={
                "type": "object",
                "properties": {
                    "anio": {"type": "integer", "description": "Año"},
                    "mes": {"type": "integer", "minimum": 1, "maximum": 12, "description": "Mes (1-12)"},
                    "quincena": {"type": "integer", "enum": [1, 2], "description": "1 (días 1-15) o 2 (días 16-fin)"},
                    "restaurante": {"type": "string", "description": "Filtrar por restaurante"}
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


# === SSE Transport para Easypanel ===

sse_transport = None


async def handle_sse(request):
    """Maneja conexiones SSE"""
    global sse_transport
    sse_transport = SseServerTransport("/messages")
    
    async with sse_transport.connect_sse(
        request.scope,
        request.receive,
        request._send
    ) as streams:
        await server.run(
            streams[0],
            streams[1],
            server.create_initialization_options()
        )


async def handle_messages(request):
    """Maneja mensajes POST del cliente"""
    if sse_transport:
        await sse_transport.handle_post_message(
            request.scope,
            request.receive,
            request._send
        )
    return JSONResponse({"status": "accepted"}, status_code=202)


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
        Route("/sse", handle_sse, methods=["GET"]),
        Route("/messages", handle_messages, methods=["POST"]),
    ]
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


async def run_sse():
    """Ejecuta el servidor en modo SSE (para Easypanel)"""
    await db.connect()
    
    port = int(os.getenv("PORT", "8000"))
    
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    server_uvicorn = uvicorn.Server(config)
    
    try:
        await server_uvicorn.serve()
    finally:
        await db.disconnect()


def main():
    """Punto de entrada principal"""
    # Si hay variable PORT, usar SSE (Easypanel), sino usar stdio (Claude Desktop)
    if os.getenv("PORT"):
        print(f"Iniciando servidor MCP en modo SSE (puerto {os.getenv('PORT')})")
        asyncio.run(run_sse())
    else:
        print("Iniciando servidor MCP en modo stdio")
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
