"""Servidor MCP para Reportes de Control de Acceso con Streamable HTTP"""

import os
import json
import asyncio
from mcp.server.fastmcp import FastMCP

from .database import Database
from .tools import empleados, registros, reportes, nomina

# Instancia de base de datos
db = Database()

# Crear servidor MCP con FastMCP
mcp = FastMCP("mcp-reportes-acceso")

# Variable para controlar si ya se conectó a la BD
_db_connected = False


async def ensure_db_connected():
    """Asegura que la base de datos esté conectada"""
    global _db_connected
    if not _db_connected:
        await db.connect()
        _db_connected = True


# ============== HERRAMIENTAS MCP ==============

@mcp.tool()
async def consultar_empleados(
    activos_solo: bool = True,
    restaurante: str = None,
    departamento: str = None
) -> str:
    """
    Lista empleados del sistema con filtros opcionales.
    
    Args:
        activos_solo: Solo empleados activos (default: True)
        restaurante: Filtrar por punto de trabajo (Bandidos|Sumo|Leños y Parrilla)
        departamento: Filtrar por departamento
    """
    await ensure_db_connected()
    result = await empleados.consultar_empleados(db, activos_solo, restaurante, departamento)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def buscar_empleado(termino: str) -> str:
    """
    Busca empleados por código, nombre o apellido.
    
    Args:
        termino: Texto a buscar (código, nombre o apellido)
    """
    await ensure_db_connected()
    result = await empleados.buscar_empleado(db, termino)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def consultar_registros_fecha(
    fecha: str,
    empleado_id: str = None,
    restaurante: str = None,
    tipo: str = None
) -> str:
    """
    Consulta registros de entrada/salida de una fecha específica.
    
    Args:
        fecha: Fecha en formato YYYY-MM-DD
        empleado_id: UUID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)
        tipo: ENTRADA o SALIDA (opcional)
    """
    await ensure_db_connected()
    result = await registros.consultar_registros_fecha(db, fecha, empleado_id, restaurante, tipo)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def consultar_registros_rango(
    fecha_inicio: str,
    fecha_fin: str,
    empleado_id: str = None,
    restaurante: str = None
) -> str:
    """
    Consulta registros en un rango de fechas.
    
    Args:
        fecha_inicio: Fecha inicio YYYY-MM-DD
        fecha_fin: Fecha fin YYYY-MM-DD
        empleado_id: UUID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)
    """
    await ensure_db_connected()
    result = await registros.consultar_registros_rango(db, fecha_inicio, fecha_fin, empleado_id, restaurante)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def calcular_horas_trabajadas_dia(empleado_id: str, fecha: str) -> str:
    """
    Calcula horas trabajadas de un empleado en un día específico con desglose de extras y recargos.
    
    Args:
        empleado_id: UUID del empleado
        fecha: Fecha en formato YYYY-MM-DD
    """
    await ensure_db_connected()
    result = await reportes.calcular_horas_trabajadas_dia(db, empleado_id, fecha)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def reporte_horas_semanal(
    empleado_id: str = None,
    fecha_semana: str = None,
    restaurante: str = None
) -> str:
    """
    Genera reporte semanal de horas trabajadas por empleado con alertas de exceso (>48h).
    
    Args:
        empleado_id: UUID del empleado (opcional, todos si no se especifica)
        fecha_semana: Cualquier fecha de la semana YYYY-MM-DD (opcional, actual si no se especifica)
        restaurante: Filtrar por restaurante (opcional)
    """
    await ensure_db_connected()
    result = await reportes.reporte_horas_semanal(db, empleado_id, fecha_semana, restaurante)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def reporte_horas_mensual(
    anio: int,
    mes: int,
    empleado_id: str = None,
    restaurante: str = None
) -> str:
    """
    Genera reporte mensual consolidado de horas y valores por empleado.
    
    Args:
        anio: Año (ej: 2024)
        mes: Mes (1-12)
        empleado_id: UUID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)
    """
    await ensure_db_connected()
    result = await reportes.reporte_horas_mensual(db, anio, mes, empleado_id, restaurante)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def obtener_ultimo_registro(empleado_id: str) -> str:
    """
    Obtiene el último registro de un empleado para saber si debe marcar entrada o salida.
    
    Args:
        empleado_id: UUID del empleado
    """
    await ensure_db_connected()
    result = await registros.obtener_ultimo_registro(db, empleado_id)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def estadisticas_asistencia(
    fecha_inicio: str,
    fecha_fin: str,
    restaurante: str = None
) -> str:
    """
    Genera estadísticas generales de asistencia para un período.
    
    Args:
        fecha_inicio: Fecha inicio YYYY-MM-DD
        fecha_fin: Fecha fin YYYY-MM-DD
        restaurante: Filtrar por restaurante (opcional)
    """
    await ensure_db_connected()
    result = await reportes.estadisticas_asistencia(db, fecha_inicio, fecha_fin, restaurante)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def empleados_sin_salida(fecha: str = None) -> str:
    """
    Lista empleados con entrada pero sin salida registrada en una fecha.
    
    Args:
        fecha: Fecha YYYY-MM-DD (default: hoy)
    """
    await ensure_db_connected()
    result = await registros.empleados_sin_salida(db, fecha)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def obtener_configuracion(clave: str = None) -> str:
    """
    Obtiene configuraciones del sistema para cálculos de nómina.
    
    Args:
        clave: Nombre de la configuración (opcional, todas si no se especifica)
    """
    await ensure_db_connected()
    result = await reportes.obtener_configuracion(db, clave)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


@mcp.tool()
async def resumen_nomina_quincenal(
    anio: int,
    mes: int,
    quincena: int,
    restaurante: str = None
) -> str:
    """
    Genera resumen para liquidación de nómina quincenal con horas y valores.
    
    Args:
        anio: Año
        mes: Mes (1-12)
        quincena: 1 (días 1-15) o 2 (días 16-fin de mes)
        restaurante: Filtrar por restaurante (opcional)
    """
    await ensure_db_connected()
    result = await nomina.resumen_nomina_quincenal(db, anio, mes, quincena, restaurante)
    return json.dumps(result, default=str, ensure_ascii=False, indent=2)


# ============== PUNTO DE ENTRADA ==============

def main():
    """Punto de entrada principal"""
    port = int(os.getenv("PORT", "8000"))
    
    # Usar transporte HTTP para despliegues remotos (Easypanel)
    # o stdio para uso local (Claude Desktop)
    if os.getenv("PORT"):
        print(f"🚀 Iniciando servidor MCP en modo HTTP (puerto {port})")
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
    else:
        print("🚀 Iniciando servidor MCP en modo stdio")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
