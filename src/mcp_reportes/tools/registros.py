"""Herramientas MCP para consulta de registros de entrada/salida"""

from typing import Optional
from datetime import datetime
from sqlalchemy import text
from ..utils.fechas import get_current_date


async def consultar_registros_fecha(
    db,
    fecha: str,
    empleado_id: Optional[str] = None,
    restaurante: Optional[str] = None,
    tipo: Optional[str] = None
) -> dict:
    """
    Consulta registros de una fecha específica.

    Args:
        db: Instancia de Database
        fecha: Fecha en formato YYYY-MM-DD
        empleado_id: UUID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)
        tipo: ENTRADA o SALIDA (opcional)

    Returns:
        Lista de registros con datos del empleado
    """
    query = """
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
          AND (CAST(:empleado_id AS uuid) IS NULL OR r.empleado_id = CAST(:empleado_id AS uuid))
          AND (CAST(:restaurante AS text) IS NULL OR r.punto_trabajo ILIKE ('%' || CAST(:restaurante AS text) || '%'))
          AND (CAST(:tipo AS text) IS NULL OR r.tipo_registro = :tipo)
        ORDER BY r.hora_registro
    """
    
    
    params = {
        'fecha': datetime.strptime(fecha, '%Y-%m-%d').date(),
        'empleado_id': empleado_id,
        'restaurante': restaurante,
        'tipo': tipo
    }
    
    results = await db.execute(query, params)
    
    registros = []
    for row in results:
        registros.append({
            'id': str(row['id']),
            'empleado_id': str(row['empleado_id']),
            'codigo_empleado': row['codigo_empleado'],
            'empleado_nombre': row['empleado_nombre'],
            'cargo': row['cargo'],
            'departamento': row['departamento'],
            'tipo_registro': row['tipo_registro'],
            'punto_trabajo': row['punto_trabajo'],
            'fecha_registro': str(row['fecha_registro']),
            'hora_registro': str(row['hora_registro']),
            'confianza': float(row['confianza_reconocimiento']) if row['confianza_reconocimiento'] else None,
            'observaciones': row['observaciones']
        })
    
    return {
        'fecha': fecha,
        'filtros': {
            'empleado_id': empleado_id,
            'restaurante': restaurante,
            'tipo': tipo
        },
        'total_registros': len(registros),
        'registros': registros
    }


async def consultar_registros_rango(
    db,
    fecha_inicio: str,
    fecha_fin: str,
    empleado_id: Optional[str] = None,
    restaurante: Optional[str] = None
) -> dict:
    """
    Consulta registros en un rango de fechas.

    Args:
        db: Instancia de Database
        fecha_inicio: Fecha inicio YYYY-MM-DD
        fecha_fin: Fecha fin YYYY-MM-DD
        empleado_id: UUID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)

    Returns:
        Lista de registros ordenados por fecha y hora
    """
    query = """
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
          AND (CAST(:empleado_id AS uuid) IS NULL OR r.empleado_id = CAST(:empleado_id AS uuid))
          AND (CAST(:restaurante AS text) IS NULL OR r.punto_trabajo ILIKE ('%' || CAST(:restaurante AS text) || '%'))
        ORDER BY r.fecha_registro, r.hora_registro
    """
    
    params = {
        'fecha_inicio': datetime.strptime(fecha_inicio, '%Y-%m-%d').date(),
        'fecha_fin': datetime.strptime(fecha_fin, '%Y-%m-%d').date(),
        'empleado_id': empleado_id,
        'restaurante': restaurante
    }
    
    results = await db.execute(query, params)
    
    registros = []
    for row in results:
        registros.append({
            'id': str(row['id']),
            'empleado_id': str(row['empleado_id']),
            'codigo_empleado': row['codigo_empleado'],
            'empleado_nombre': row['empleado_nombre'],
            'tipo_registro': row['tipo_registro'],
            'punto_trabajo': row['punto_trabajo'],
            'fecha_registro': str(row['fecha_registro']),
            'hora_registro': str(row['hora_registro']),
            'observaciones': row['observaciones']
        })
    
    return {
        'periodo': {
            'inicio': fecha_inicio,
            'fin': fecha_fin
        },
        'filtros': {
            'empleado_id': empleado_id,
            'restaurante': restaurante
        },
        'total_registros': len(registros),
        'registros': registros
    }


async def obtener_ultimo_registro(db, empleado_id: str) -> dict:
    """
    Obtiene el último registro de un empleado.

    Args:
        db: Instancia de Database
        empleado_id: UUID del empleado

    Returns:
        Último registro y siguiente acción esperada
    """
    query = """
        SELECT
            r.tipo_registro,
            r.fecha_registro,
            r.hora_registro,
            r.punto_trabajo,
            e.nombre || ' ' || e.apellido AS empleado_nombre
        FROM registros r
        JOIN empleados e ON r.empleado_id = e.id
        WHERE r.empleado_id = CAST(:empleado_id AS uuid)
        ORDER BY r.fecha_registro DESC, r.hora_registro DESC
        LIMIT 1
    """
    
    result = await db.execute_one(query, {'empleado_id': empleado_id})
    
    if result:
        siguiente_accion = 'SALIDA' if result['tipo_registro'] == 'ENTRADA' else 'ENTRADA'
        return {
            'empleado_id': empleado_id,
            'empleado_nombre': result['empleado_nombre'],
            'ultimo_registro': {
                'tipo': result['tipo_registro'],
                'fecha': str(result['fecha_registro']),
                'hora': str(result['hora_registro']),
                'punto_trabajo': result['punto_trabajo']
            },
            'siguiente_accion': siguiente_accion
        }
    else:
        return {
            'empleado_id': empleado_id,
            'empleado_nombre': None,
            'ultimo_registro': None,
            'siguiente_accion': 'ENTRADA',
            'mensaje': 'No hay registros para este empleado'
        }


async def empleados_sin_salida(db, fecha: Optional[str] = None) -> dict:
    """
    Lista empleados con entrada pero sin salida registrada.

    Args:
        db: Instancia de Database
        fecha: Fecha YYYY-MM-DD (opcional, default: hoy)

    Returns:
        Lista de empleados pendientes
    """
    if fecha is None:
        fecha = str(get_current_date())
    
    query = """
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
            EXTRACT(EPOCH FROM (NOW() - (CAST(:fecha AS date) + en.primera_entrada))) / 3600 AS horas_transcurridas
        FROM entradas en
        JOIN empleados e ON en.empleado_id = e.id
        LEFT JOIN salidas s ON en.empleado_id = s.empleado_id
        WHERE s.empleado_id IS NULL
        ORDER BY en.primera_entrada
    """
    
    results = await db.execute(query, {'fecha': fecha})
    
    empleados = []
    for row in results:
        empleados.append({
            'empleado_id': str(row['empleado_id']),
            'codigo_empleado': row['codigo_empleado'],
            'empleado_nombre': row['empleado_nombre'],
            'hora_entrada': str(row['hora_entrada']),
            'punto_trabajo': row['punto_trabajo'],
            'horas_transcurridas': round(float(row['horas_transcurridas']), 2) if row['horas_transcurridas'] else 0
        })
    
    return {
        'fecha': fecha,
        'total_sin_salida': len(empleados),
        'empleados': empleados
    }

async def maintenance_fusionar_empleados(db, id_origen: str, id_destino: str, nuevo_codigo: str) -> dict:
    """
    Fusiona dos registros de empleados:
    1. Limpia código en origen (para evitar conflictos de UNIQUE).
    2. Migra todos los registros de id_origen a id_destino.
    3. Actualiza el código de id_destino.
    4. Elimina id_origen.
    """
    import uuid
    temp_code = f"temp_{uuid.uuid4().hex[:8]}"
    
    try:
        async with db.session_factory() as session:
            # 1. Limpiar código en origen (evitar IntegrityError por UNIQUE constraint)
            q_clear = text("UPDATE empleados SET codigo_empleado = :tmp WHERE id = :orig")
            await session.execute(q_clear, {"tmp": temp_code, "orig": id_origen})
            
            # 2. Contar registros a migrar
            q_count = text("SELECT COUNT(*) FROM registros WHERE empleado_id = :orig")
            res_count = await session.execute(q_count, {"orig": id_origen})
            count = res_count.scalar()
            
            # 3. Migrar registros
            if count > 0:
                q_migrate = text("UPDATE registros SET empleado_id = :dest WHERE empleado_id = :orig")
                await session.execute(q_migrate, {"dest": id_destino, "orig": id_origen})
            
            # 4. Actualizar código en destino
            q_update = text("UPDATE empleados SET codigo_empleado = :cod WHERE id = :dest")
            await session.execute(q_update, {"cod": nuevo_codigo, "dest": id_destino})
            
            # 5. Eliminar origen
            q_delete = text("DELETE FROM empleados WHERE id = :orig")
            await session.execute(q_delete, {"orig": id_origen})
            
            await session.commit()
            
            return {
                "status": "success",
                "registros_migrados": count,
                "mensaje": f"Alexis fusionado correctamente. Código {nuevo_codigo} asignado a {id_destino}."
            }
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


