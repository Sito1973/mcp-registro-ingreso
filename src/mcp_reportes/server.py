"""Servidor MCP para Reportes de Control de Acceso con Streamable HTTP"""

import os
import json
import contextlib
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse
import uvicorn
from .database import Database
from .tools import empleados, registros, reportes, nomina

# Instancia de base de datos
db = Database()

# Crear servidor MCP con Streamable HTTP
mcp = FastMCP(
    "mcp-reportes-acceso",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/mcp",
)


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


def create_starlette_app():
    """Crea la aplicación Starlette con el servidor MCP montado"""

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        """Maneja el ciclo de vida de la aplicación"""
        # Conectar base de datos
        await db.connect()
        print("Base de datos conectada")

        # Iniciar el session manager de MCP
        async with mcp.session_manager.run():
            yield

        # Desconectar base de datos
        await db.disconnect()
        print("Base de datos desconectada")

    # Obtener la app MCP con el path configurado
    mcp_app = mcp.streamable_http_app()

    app = Starlette(
        routes=[
            Route("/health", health_check, methods=["GET"]),
            # Montar en root para evitar problemas de path
            Mount("/", app=mcp_app),
        ],
        lifespan=lifespan,
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
