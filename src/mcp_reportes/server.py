"""Servidor MCP para Reportes de Control de Acceso con Streamable HTTP"""

import os
import json
import contextlib
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn
from .database import Database
from .tools import empleados, registros, reportes, nomina

# Instancia de base de datos
db = Database()

# Crear servidor MCP (solo para stdio mode y definición de tools)
mcp = FastMCP("mcp-reportes-acceso")


# === HERRAMIENTAS DE EMPLEADOS ===

@mcp.tool()
async def consultar_empleados(
    activos_solo: bool = True,
    restaurante: str | None = None,
    departamento: str | None = None
) -> str:
    """Lista empleados del sistema con filtros opcionales por restaurante y departamento"""
    result = await empleados.consultar_empleados(
        db,
        activos_solo=activos_solo,
        restaurante=restaurante,
        departamento=departamento
    )
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def buscar_empleado(termino: str) -> str:
    """Busca empleados por código, nombre o apellido"""
    result = await empleados.buscar_empleado(db, termino=termino)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


# === HERRAMIENTAS DE REGISTROS ===

@mcp.tool()
async def consultar_registros_fecha(
    fecha: str,
    empleado_id: str | None = None,
    restaurante: str | None = None,
    tipo: str | None = None
) -> str:
    """Consulta registros de entrada/salida de una fecha específica.

    Args:
        fecha: Fecha en formato YYYY-MM-DD
        empleado_id: ID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)
        tipo: Tipo de registro: ENTRADA o SALIDA (opcional)
    """
    result = await registros.consultar_registros_fecha(
        db,
        fecha=fecha,
        empleado_id=empleado_id,
        restaurante=restaurante,
        tipo=tipo
    )
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def consultar_registros_rango(
    fecha_inicio: str,
    fecha_fin: str,
    empleado_id: str | None = None,
    restaurante: str | None = None
) -> str:
    """Consulta registros en un rango de fechas.

    Args:
        fecha_inicio: Fecha inicial en formato YYYY-MM-DD
        fecha_fin: Fecha final en formato YYYY-MM-DD
        empleado_id: ID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)
    """
    result = await registros.consultar_registros_rango(
        db,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        empleado_id=empleado_id,
        restaurante=restaurante
    )
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def obtener_ultimo_registro(empleado_id: str) -> str:
    """Obtiene el último registro de un empleado"""
    result = await registros.obtener_ultimo_registro(db, empleado_id=empleado_id)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def empleados_sin_salida(fecha: str | None = None) -> str:
    """Lista empleados con entrada pero sin salida en una fecha.

    Args:
        fecha: Fecha en formato YYYY-MM-DD (opcional, default: hoy)
    """
    result = await registros.empleados_sin_salida(db, fecha=fecha)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


# === HERRAMIENTAS DE REPORTES ===

@mcp.tool()
async def calcular_horas_trabajadas_dia(empleado_id: str, fecha: str) -> str:
    """Calcula horas trabajadas de un empleado en un día con desglose de extras.

    Args:
        empleado_id: ID del empleado
        fecha: Fecha en formato YYYY-MM-DD
    """
    result = await reportes.calcular_horas_trabajadas_dia(
        db,
        empleado_id=empleado_id,
        fecha=fecha
    )
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def reporte_horas_semanal(
    empleado_id: str | None = None,
    fecha_semana: str | None = None,
    restaurante: str | None = None
) -> str:
    """Genera reporte semanal de horas trabajadas por empleado.

    Args:
        empleado_id: ID del empleado (opcional)
        fecha_semana: Cualquier fecha de la semana en formato YYYY-MM-DD (opcional)
        restaurante: Filtrar por restaurante (opcional)
    """
    result = await reportes.reporte_horas_semanal(
        db,
        empleado_id=empleado_id,
        fecha_semana=fecha_semana,
        restaurante=restaurante
    )
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def reporte_horas_mensual(
    anio: int,
    mes: int,
    empleado_id: str | None = None,
    restaurante: str | None = None
) -> str:
    """Genera reporte mensual consolidado de horas por empleado.

    Args:
        anio: Año (ej: 2025)
        mes: Mes (1-12)
        empleado_id: ID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)
    """
    result = await reportes.reporte_horas_mensual(
        db,
        anio=anio,
        mes=mes,
        empleado_id=empleado_id,
        restaurante=restaurante
    )
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def estadisticas_asistencia(
    fecha_inicio: str,
    fecha_fin: str,
    restaurante: str | None = None
) -> str:
    """Genera estadísticas de asistencia para un período.

    Args:
        fecha_inicio: Fecha inicial en formato YYYY-MM-DD
        fecha_fin: Fecha final en formato YYYY-MM-DD
        restaurante: Filtrar por restaurante (opcional)
    """
    result = await reportes.estadisticas_asistencia(
        db,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        restaurante=restaurante
    )
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def obtener_configuracion(clave: str | None = None) -> str:
    """Obtiene configuraciones del sistema para nómina.

    Args:
        clave: Clave de configuración específica (opcional)
    """
    result = await reportes.obtener_configuracion(db, clave=clave)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


# === HERRAMIENTAS DE NÓMINA ===

@mcp.tool()
async def resumen_nomina_quincenal(
    anio: int,
    mes: int,
    quincena: int,
    restaurante: str | None = None
) -> str:
    """Genera resumen para liquidación de nómina quincenal.

    Args:
        anio: Año (ej: 2025)
        mes: Mes (1-12)
        quincena: Quincena (1 o 2)
        restaurante: Filtrar por restaurante (opcional)
    """
    result = await nomina.resumen_nomina_quincenal(
        db,
        anio=anio,
        mes=mes,
        quincena=quincena,
        restaurante=restaurante
    )
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


async def health_check(request):
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "server": "mcp-reportes-acceso",
        "version": "2.0.0",
        "transport": "streamable-http"
    })


# ============================================================================
# Manual Streamable HTTP Handler (bypasses DNS rebinding protection issues)
# ============================================================================

# Registry of tool functions for direct invocation
TOOL_REGISTRY = {
    "consultar_empleados": lambda args: empleados.consultar_empleados(
        db,
        activos_solo=args.get("activos_solo", True),
        restaurante=args.get("restaurante"),
        departamento=args.get("departamento")
    ),
    "buscar_empleado": lambda args: empleados.buscar_empleado(
        db, termino=args.get("termino", "")
    ),
    "consultar_registros_fecha": lambda args: registros.consultar_registros_fecha(
        db,
        fecha=args.get("fecha", ""),
        empleado_id=args.get("empleado_id"),
        restaurante=args.get("restaurante"),
        tipo=args.get("tipo")
    ),
    "consultar_registros_rango": lambda args: registros.consultar_registros_rango(
        db,
        fecha_inicio=args.get("fecha_inicio", ""),
        fecha_fin=args.get("fecha_fin", ""),
        empleado_id=args.get("empleado_id"),
        restaurante=args.get("restaurante")
    ),
    "obtener_ultimo_registro": lambda args: registros.obtener_ultimo_registro(
        db, empleado_id=args.get("empleado_id", "")
    ),
    "empleados_sin_salida": lambda args: registros.empleados_sin_salida(
        db, fecha=args.get("fecha")
    ),
    "calcular_horas_trabajadas_dia": lambda args: reportes.calcular_horas_trabajadas_dia(
        db,
        empleado_id=args.get("empleado_id", ""),
        fecha=args.get("fecha", "")
    ),
    "reporte_horas_semanal": lambda args: reportes.reporte_horas_semanal(
        db,
        empleado_id=args.get("empleado_id"),
        fecha_semana=args.get("fecha_semana"),
        restaurante=args.get("restaurante")
    ),
    "reporte_horas_mensual": lambda args: reportes.reporte_horas_mensual(
        db,
        anio=args.get("anio", 2025),
        mes=args.get("mes", 1),
        empleado_id=args.get("empleado_id"),
        restaurante=args.get("restaurante")
    ),
    "estadisticas_asistencia": lambda args: reportes.estadisticas_asistencia(
        db,
        fecha_inicio=args.get("fecha_inicio", ""),
        fecha_fin=args.get("fecha_fin", ""),
        restaurante=args.get("restaurante")
    ),
    "obtener_configuracion": lambda args: reportes.obtener_configuracion(
        db, clave=args.get("clave")
    ),
    "resumen_nomina_quincenal": lambda args: nomina.resumen_nomina_quincenal(
        db,
        anio=args.get("anio", 2025),
        mes=args.get("mes", 1),
        quincena=args.get("quincena", 1),
        restaurante=args.get("restaurante")
    ),
}

# Tool definitions for tools/list response
TOOL_DEFINITIONS = [
    {
        "name": "consultar_empleados",
        "description": "Lista empleados del sistema con filtros opcionales por restaurante y departamento",
        "inputSchema": {
            "type": "object",
            "properties": {
                "activos_solo": {"type": "boolean", "default": True, "description": "Solo empleados activos"},
                "restaurante": {"type": "string", "description": "Filtrar por restaurante"},
                "departamento": {"type": "string", "description": "Filtrar por departamento"}
            }
        }
    },
    {
        "name": "buscar_empleado",
        "description": "Busca empleados por código, nombre o apellido",
        "inputSchema": {
            "type": "object",
            "properties": {
                "termino": {"type": "string", "description": "Término de búsqueda"}
            },
            "required": ["termino"]
        }
    },
    {
        "name": "consultar_registros_fecha",
        "description": "Consulta registros de entrada/salida de una fecha específica",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fecha": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
                "empleado_id": {"type": "string", "description": "ID del empleado"},
                "restaurante": {"type": "string", "description": "Filtrar por restaurante"},
                "tipo": {"type": "string", "description": "Tipo de registro: ENTRADA o SALIDA"}
            },
            "required": ["fecha"]
        }
    },
    {
        "name": "consultar_registros_rango",
        "description": "Consulta registros en un rango de fechas",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fecha_inicio": {"type": "string", "description": "Fecha inicial YYYY-MM-DD"},
                "fecha_fin": {"type": "string", "description": "Fecha final YYYY-MM-DD"},
                "empleado_id": {"type": "string", "description": "ID del empleado"},
                "restaurante": {"type": "string", "description": "Filtrar por restaurante"}
            },
            "required": ["fecha_inicio", "fecha_fin"]
        }
    },
    {
        "name": "obtener_ultimo_registro",
        "description": "Obtiene el último registro de un empleado",
        "inputSchema": {
            "type": "object",
            "properties": {
                "empleado_id": {"type": "string", "description": "ID del empleado"}
            },
            "required": ["empleado_id"]
        }
    },
    {
        "name": "empleados_sin_salida",
        "description": "Lista empleados con entrada pero sin salida en una fecha",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fecha": {"type": "string", "description": "Fecha YYYY-MM-DD (default: hoy)"}
            }
        }
    },
    {
        "name": "calcular_horas_trabajadas_dia",
        "description": "Calcula horas trabajadas de un empleado en un día con desglose de extras",
        "inputSchema": {
            "type": "object",
            "properties": {
                "empleado_id": {"type": "string", "description": "ID del empleado"},
                "fecha": {"type": "string", "description": "Fecha YYYY-MM-DD"}
            },
            "required": ["empleado_id", "fecha"]
        }
    },
    {
        "name": "reporte_horas_semanal",
        "description": "Genera reporte semanal de horas trabajadas por empleado",
        "inputSchema": {
            "type": "object",
            "properties": {
                "empleado_id": {"type": "string", "description": "ID del empleado"},
                "fecha_semana": {"type": "string", "description": "Cualquier fecha de la semana YYYY-MM-DD"},
                "restaurante": {"type": "string", "description": "Filtrar por restaurante"}
            }
        }
    },
    {
        "name": "reporte_horas_mensual",
        "description": "Genera reporte mensual consolidado de horas por empleado",
        "inputSchema": {
            "type": "object",
            "properties": {
                "anio": {"type": "integer", "description": "Año (ej: 2025)"},
                "mes": {"type": "integer", "description": "Mes (1-12)"},
                "empleado_id": {"type": "string", "description": "ID del empleado"},
                "restaurante": {"type": "string", "description": "Filtrar por restaurante"}
            },
            "required": ["anio", "mes"]
        }
    },
    {
        "name": "estadisticas_asistencia",
        "description": "Genera estadísticas de asistencia para un período",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fecha_inicio": {"type": "string", "description": "Fecha inicial YYYY-MM-DD"},
                "fecha_fin": {"type": "string", "description": "Fecha final YYYY-MM-DD"},
                "restaurante": {"type": "string", "description": "Filtrar por restaurante"}
            },
            "required": ["fecha_inicio", "fecha_fin"]
        }
    },
    {
        "name": "obtener_configuracion",
        "description": "Obtiene configuraciones del sistema para nómina",
        "inputSchema": {
            "type": "object",
            "properties": {
                "clave": {"type": "string", "description": "Clave de configuración específica"}
            }
        }
    },
    {
        "name": "resumen_nomina_quincenal",
        "description": "Genera resumen para liquidación de nómina quincenal",
        "inputSchema": {
            "type": "object",
            "properties": {
                "anio": {"type": "integer", "description": "Año (ej: 2025)"},
                "mes": {"type": "integer", "description": "Mes (1-12)"},
                "quincena": {"type": "integer", "description": "Quincena (1 o 2)"},
                "restaurante": {"type": "string", "description": "Filtrar por restaurante"}
            },
            "required": ["anio", "mes", "quincena"]
        }
    },
]


async def handle_streamable_http(request: Request):
    """
    Handle Streamable HTTP MCP requests.
    This bypasses FastMCP's DNS rebinding protection for EasyPanel compatibility.
    """
    import sys

    method = request.method
    print(f"[Streamable HTTP] {method} /mcp", file=sys.stderr)

    if method == "GET":
        # Return server info for discovery
        return JSONResponse({
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "mcp-reportes-acceso",
                    "version": "2.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        })

    if method == "POST":
        try:
            body = await request.json()
            print(f"[Streamable HTTP] Request: {json.dumps(body)[:200]}", file=sys.stderr)

            method_name = body.get("method", "")
            msg_id = body.get("id")
            params = body.get("params", {})

            # Handle notifications (no response needed but n8n expects one)
            if method_name.startswith("notifications/"):
                if msg_id is not None:
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {}
                    })
                return JSONResponse({"jsonrpc": "2.0", "result": {}})

            if method_name == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {
                            "name": "mcp-reportes-acceso",
                            "version": "2.0.0"
                        },
                        "capabilities": {
                            "tools": {}
                        }
                    }
                }
                print(f"[Streamable HTTP] Initialize response sent", file=sys.stderr)
                return JSONResponse(response)

            elif method_name == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": TOOL_DEFINITIONS}
                }
                print(f"[Streamable HTTP] Tools list: {len(TOOL_DEFINITIONS)} tools", file=sys.stderr)
                return JSONResponse(response)

            elif method_name == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})

                print(f"[Streamable HTTP] Calling tool: {tool_name}", file=sys.stderr)

                if tool_name not in TOOL_REGISTRY:
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
                    })

                try:
                    # Call the tool function
                    result = await TOOL_REGISTRY[tool_name](tool_args)

                    # Format result as JSON string
                    text_content = json.dumps(result, default=str, ensure_ascii=False, indent=2)

                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": text_content}]
                        }
                    }
                    print(f"[Streamable HTTP] Tool {tool_name} executed successfully", file=sys.stderr)
                    return JSONResponse(response)

                except Exception as e:
                    print(f"[Streamable HTTP] Tool error: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": -32000, "message": str(e)}
                    })

            else:
                # Unknown method
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method_name}"}
                })

        except Exception as e:
            print(f"[Streamable HTTP ERROR] {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return JSONResponse(
                {"jsonrpc": "2.0", "error": {"code": -32000, "message": str(e)}},
                status_code=500
            )

    return JSONResponse({"error": "Method not allowed"}, status_code=405)


def create_starlette_app():
    """Crea la aplicación Starlette con el handler Streamable HTTP manual"""

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        """Maneja el ciclo de vida de la aplicación"""
        # Conectar base de datos
        await db.connect()
        print("Base de datos conectada")
        yield
        # Desconectar base de datos
        await db.disconnect()
        print("Base de datos desconectada")

    app = Starlette(
        routes=[
            Route("/", health_check, methods=["GET"]),
            Route("/health", health_check, methods=["GET"]),
            Route("/mcp", handle_streamable_http, methods=["GET", "POST"]),
        ],
        lifespan=lifespan,
    )

    # Añadir CORS Middleware para permitir acceso desde ChatKit/Web
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


def main():
    """Punto de entrada principal"""
    port = int(os.getenv("PORT", "8000"))

    if os.getenv("PORT"):
        # Modo Streamable HTTP para deployment
        print(f"Iniciando servidor MCP con Streamable HTTP (puerto {port})")

        app = create_starlette_app()

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
    else:
        # Modo stdio para Claude Desktop local
        print("Iniciando servidor MCP en modo stdio")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
