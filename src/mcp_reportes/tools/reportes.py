"""Herramientas MCP para reportes de horas y estadísticas"""

from typing import Optional
from datetime import date, datetime
from ..utils.fechas import get_current_date, get_week_range, get_month_range, format_date
from ..utils.calculos import calcular_horas_dia, calcular_valor_horas, LIMITE_SEMANAL


async def calcular_horas_trabajadas_dia(db, empleado_id: str, fecha: str) -> dict:
    """
    Calcula las horas trabajadas de un empleado en una fecha.

    Args:
        db: Instancia de Database
        empleado_id: UUID del empleado
        fecha: Fecha en formato YYYY-MM-DD

    Returns:
        Desglose de horas trabajadas
    """
    # Obtener datos del empleado
    empleado_query = """
        SELECT nombre || ' ' || apellido AS nombre, liquida_dominical
        FROM empleados WHERE id = :empleado_id::uuid
    """
    empleado = await db.execute_one(empleado_query, {'empleado_id': empleado_id})
    
    if not empleado:
        return {'error': f'Empleado {empleado_id} no encontrado'}
    
    # Obtener registros del día
    registros_query = """
        SELECT
            tipo_registro,
            hora_registro,
            observaciones
        FROM registros
        WHERE empleado_id = :empleado_id::uuid
          AND fecha_registro = :fecha
        ORDER BY hora_registro
    """
    
    registros = await db.execute(registros_query, {
        'empleado_id': empleado_id,
        'fecha': fecha
    })
    
    if not registros:
        return {
            'empleado_id': empleado_id,
            'empleado_nombre': empleado['nombre'],
            'fecha': fecha,
            'mensaje': 'No hay registros para esta fecha',
            'horas_trabajadas': 0
        }
    
    # Calcular horas
    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
    resultado = calcular_horas_dia(registros, fecha_obj)
    
    # Agregar info del empleado
    resultado['empleado_id'] = empleado_id
    resultado['empleado_nombre'] = empleado['nombre']
    resultado['liquida_dominical'] = empleado['liquida_dominical']
    
    # Agregar registros crudos para referencia
    resultado['registros'] = [
        {'tipo': r['tipo_registro'], 'hora': str(r['hora_registro']), 'obs': r['observaciones']}
        for r in registros
    ]
    
    return resultado


async def reporte_horas_semanal(
    db,
    empleado_id: Optional[str] = None,
    fecha_semana: Optional[str] = None,
    restaurante: Optional[str] = None
) -> dict:
    """
    Genera reporte semanal de horas trabajadas.

    Args:
        db: Instancia de Database
        empleado_id: UUID del empleado (opcional)
        fecha_semana: Cualquier fecha de la semana (opcional)
        restaurante: Filtrar por restaurante (opcional)

    Returns:
        Reporte semanal por empleado
    """
    # Determinar rango de la semana
    if fecha_semana:
        fecha_ref = datetime.strptime(fecha_semana, '%Y-%m-%d').date()
    else:
        fecha_ref = get_current_date()
    
    inicio_semana, fin_semana = get_week_range(fecha_ref)
    
    # Obtener registros de la semana
    query = """
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
            EXTRACT(DOW FROM r.fecha_registro) AS dia_semana
        FROM registros r
        JOIN empleados e ON r.empleado_id = e.id
        WHERE r.fecha_registro BETWEEN :inicio AND :fin
          AND (:empleado_id IS NULL OR r.empleado_id = :empleado_id::uuid)
          AND (:restaurante IS NULL OR r.punto_trabajo = :restaurante)
          AND e.activo = TRUE
        ORDER BY e.apellido, e.nombre, r.fecha_registro, r.hora_registro
    """
    
    results = await db.execute(query, {
        'inicio': str(inicio_semana),
        'fin': str(fin_semana),
        'empleado_id': empleado_id,
        'restaurante': restaurante
    })
    
    # Agrupar por empleado
    empleados_data = {}
    for row in results:
        emp_id = str(row['empleado_id'])
        if emp_id not in empleados_data:
            empleados_data[emp_id] = {
                'empleado_id': emp_id,
                'codigo': row['codigo_empleado'],
                'nombre': row['empleado_nombre'],
                'liquida_dominical': row['liquida_dominical'],
                'registros_por_fecha': {}
            }
        
        fecha = str(row['fecha_registro'])
        if fecha not in empleados_data[emp_id]['registros_por_fecha']:
            empleados_data[emp_id]['registros_por_fecha'][fecha] = []
        
        empleados_data[emp_id]['registros_por_fecha'][fecha].append({
            'tipo_registro': row['tipo_registro'],
            'hora_registro': row['hora_registro']
        })
    
    # Calcular horas por empleado
    reportes = []
    for emp_id, data in empleados_data.items():
        dias = []
        totales = {
            'horas_trabajadas': 0,
            'horas_ordinarias': 0,
            'horas_extra_diurna': 0,
            'horas_extra_nocturna': 0,
            'horas_recargo_nocturno': 0,
            'horas_dominical': 0
        }
        
        for fecha_str, registros in data['registros_por_fecha'].items():
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            horas_dia = calcular_horas_dia(registros, fecha_obj)
            horas_dia['fecha'] = fecha_str
            dias.append(horas_dia)
            
            for key in totales:
                totales[key] += horas_dia.get(key, 0)
        
        # Redondear totales
        for key in totales:
            totales[key] = round(totales[key], 2)
        
        # Verificar exceso de horas
        alerta_exceso = totales['horas_trabajadas'] > LIMITE_SEMANAL
        horas_exceso = max(0, totales['horas_trabajadas'] - LIMITE_SEMANAL)
        
        reportes.append({
            'empleado_id': emp_id,
            'codigo': data['codigo'],
            'nombre': data['nombre'],
            'semana_inicio': str(inicio_semana),
            'semana_fin': str(fin_semana),
            'dias': dias,
            'totales': totales,
            'alerta_exceso': alerta_exceso,
            'horas_exceso': round(horas_exceso, 2)
        })
    
    return {
        'semana': {
            'inicio': str(inicio_semana),
            'fin': str(fin_semana)
        },
        'filtros': {
            'empleado_id': empleado_id,
            'restaurante': restaurante
        },
        'total_empleados': len(reportes),
        'reportes': reportes
    }


async def reporte_horas_mensual(
    db,
    anio: int,
    mes: int,
    empleado_id: Optional[str] = None,
    restaurante: Optional[str] = None
) -> dict:
    """
    Genera reporte mensual consolidado por empleado.

    Args:
        db: Instancia de Database
        anio: Año
        mes: Mes (1-12)
        empleado_id: UUID del empleado (opcional)
        restaurante: Filtrar por restaurante (opcional)

    Returns:
        Reporte mensual por empleado
    """
    inicio_mes, fin_mes = get_month_range(anio, mes)
    
    meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    periodo = f"{meses[mes]} {anio}"
    
    query = """
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
        ORDER BY e.apellido, e.nombre, r.fecha_registro, r.hora_registro
    """
    
    results = await db.execute(query, {
        'anio': anio,
        'mes': mes,
        'empleado_id': empleado_id,
        'restaurante': restaurante
    })
    
    # Agrupar por empleado
    empleados_data = {}
    for row in results:
        emp_id = str(row['empleado_id'])
        if emp_id not in empleados_data:
            empleados_data[emp_id] = {
                'empleado_id': emp_id,
                'codigo': row['codigo_empleado'],
                'nombre': f"{row['nombre']} {row['apellido']}",
                'cargo': row['cargo'],
                'departamento': row['departamento'],
                'liquida_dominical': row['liquida_dominical'],
                'registros_por_fecha': {}
            }
        
        fecha = str(row['fecha_registro'])
        if fecha not in empleados_data[emp_id]['registros_por_fecha']:
            empleados_data[emp_id]['registros_por_fecha'][fecha] = []
        
        empleados_data[emp_id]['registros_por_fecha'][fecha].append({
            'tipo_registro': row['tipo_registro'],
            'hora_registro': row['hora_registro']
        })
    
    # Calcular por empleado
    reportes = []
    for emp_id, data in empleados_data.items():
        resumen = {
            'dias_trabajados': len(data['registros_por_fecha']),
            'total_horas': 0,
            'horas_ordinarias': 0,
            'horas_extra_diurna': 0,
            'horas_extra_nocturna': 0,
            'recargo_nocturno': 0,
            'horas_dominical': 0
        }
        
        for fecha_str, registros in data['registros_por_fecha'].items():
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            horas_dia = calcular_horas_dia(registros, fecha_obj)
            
            resumen['total_horas'] += horas_dia['horas_trabajadas']
            resumen['horas_ordinarias'] += horas_dia['horas_ordinarias']
            resumen['horas_extra_diurna'] += horas_dia['horas_extra_diurna']
            resumen['horas_extra_nocturna'] += horas_dia['horas_extra_nocturna']
            resumen['recargo_nocturno'] += horas_dia['horas_recargo_nocturno']
            resumen['horas_dominical'] += horas_dia['horas_dominical']
        
        # Redondear
        for key in resumen:
            if key != 'dias_trabajados':
                resumen[key] = round(resumen[key], 2)
        
        reportes.append({
            'empleado_id': emp_id,
            'codigo': data['codigo'],
            'nombre': data['nombre'],
            'cargo': data['cargo'],
            'departamento': data['departamento'],
            'periodo': periodo,
            'resumen': resumen
        })
    
    return {
        'periodo': periodo,
        'rango': {
            'inicio': str(inicio_mes),
            'fin': str(fin_mes)
        },
        'filtros': {
            'empleado_id': empleado_id,
            'restaurante': restaurante
        },
        'total_empleados': len(reportes),
        'reportes': reportes
    }


async def estadisticas_asistencia(
    db,
    fecha_inicio: str,
    fecha_fin: str,
    restaurante: Optional[str] = None
) -> dict:
    """
    Genera estadísticas generales de asistencia.

    Args:
        db: Instancia de Database
        fecha_inicio: Fecha inicio YYYY-MM-DD
        fecha_fin: Fecha fin YYYY-MM-DD
        restaurante: Filtrar por restaurante (opcional)

    Returns:
        Estadísticas del período
    """
    query = """
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
        GROUP BY punto_trabajo
    """
    
    results = await db.execute(query, {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'restaurante': restaurante
    })
    
    totales = {
        'total_registros': 0,
        'empleados_unicos': 0,
        'entradas': 0,
        'salidas': 0,
        'registros_forzados': 0
    }
    
    por_restaurante = []
    for row in results:
        totales['total_registros'] += row['total_registros']
        totales['entradas'] += row['entradas']
        totales['salidas'] += row['salidas']
        totales['registros_forzados'] += row['forzados']
        
        por_restaurante.append({
            'restaurante': row['punto_trabajo'],
            'registros': row['total_registros'],
            'empleados': row['empleados_unicos']
        })
    
    # Obtener empleados únicos totales
    query_empleados = """
        SELECT COUNT(DISTINCT empleado_id) AS total
        FROM registros
        WHERE fecha_registro BETWEEN :fecha_inicio AND :fecha_fin
          AND (:restaurante IS NULL OR punto_trabajo = :restaurante)
    """
    emp_result = await db.execute_one(query_empleados, {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'restaurante': restaurante
    })
    totales['empleados_unicos'] = emp_result['total'] if emp_result else 0
    
    return {
        'periodo': {
            'inicio': fecha_inicio,
            'fin': fecha_fin
        },
        'totales': totales,
        'por_restaurante': por_restaurante
    }


async def obtener_configuracion(db, clave: Optional[str] = None) -> dict:
    """
    Obtiene configuraciones del sistema.

    Args:
        db: Instancia de Database
        clave: Nombre de la configuración (opcional)

    Returns:
        Configuración o lista de configuraciones
    """
    query = """
        SELECT clave, valor, descripcion, tipo_dato
        FROM configuracion
        WHERE (:clave::text IS NULL OR clave = :clave)
        ORDER BY clave
    """
    
    results = await db.execute(query, {'clave': clave})
    
    if clave and results:
        row = results[0]
        return {
            'clave': row['clave'],
            'valor': row['valor'],
            'descripcion': row['descripcion'],
            'tipo_dato': row['tipo_dato']
        }
    
    configuraciones = []
    for row in results:
        configuraciones.append({
            'clave': row['clave'],
            'valor': row['valor'],
            'descripcion': row['descripcion'],
            'tipo_dato': row['tipo_dato']
        })
    
    return {
        'total': len(configuraciones),
        'configuraciones': configuraciones
    }
