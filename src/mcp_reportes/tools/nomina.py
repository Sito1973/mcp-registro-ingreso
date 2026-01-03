"""Herramientas MCP para reportes de nómina"""

from typing import Optional
from datetime import datetime
from ..utils.fechas import get_quincena_range
from ..utils.calculos import calcular_horas_dia, calcular_valor_horas


async def resumen_nomina_quincenal(
    db,
    anio: int,
    mes: int,
    quincena: int,
    restaurante: Optional[str] = None
) -> dict:
    """
    Genera resumen para liquidación de nómina quincenal.

    Args:
        db: Instancia de Database
        anio: Año
        mes: Mes (1-12)
        quincena: 1 (días 1-15) o 2 (días 16-fin de mes)
        restaurante: Filtrar por restaurante (opcional)

    Returns:
        Resumen de nómina por empleado
    """
    inicio, fin = get_quincena_range(anio, mes, quincena)
    
    meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    periodo = f"Quincena {quincena} - {meses[mes]} {anio}"
    
    # Obtener configuración de valores
    config_query = """
        SELECT clave, valor FROM configuracion
        WHERE clave IN ('valor_hora_ordinaria', 'valor_hora_extra_diurna', 'valor_hora_extra_nocturna')
    """
    config_results = await db.execute(config_query, {})
    config = {row['clave']: row['valor'] for row in config_results}
    
    # Obtener registros de la quincena
    query = """
        SELECT
            r.empleado_id,
            e.codigo_empleado,
            e.nombre || ' ' || e.apellido AS nombre,
            e.cargo,
            e.departamento,
            e.liquida_dominical,
            r.fecha_registro,
            r.tipo_registro,
            r.hora_registro,
            r.observaciones
        FROM registros r
        JOIN empleados e ON r.empleado_id = e.id
        WHERE r.fecha_registro BETWEEN :inicio AND :fin
          AND (:restaurante IS NULL OR r.punto_trabajo = :restaurante)
          AND e.activo = TRUE
        ORDER BY e.apellido, e.nombre, r.fecha_registro, r.hora_registro
    """
    
    results = await db.execute(query, {
        'inicio': str(inicio),
        'fin': str(fin),
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
                'nombre': row['nombre'],
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
        horas = {
            'ordinarias': 0,
            'extra_diurna': 0,
            'extra_nocturna': 0,
            'recargo_nocturno': 0,
            'dominical': 0
        }
        
        detalle_dias = []
        
        for fecha_str, registros in data['registros_por_fecha'].items():
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            horas_dia = calcular_horas_dia(registros, fecha_obj)
            
            horas['ordinarias'] += horas_dia['horas_ordinarias']
            horas['extra_diurna'] += horas_dia['horas_extra_diurna']
            horas['extra_nocturna'] += horas_dia['horas_extra_nocturna']
            horas['recargo_nocturno'] += horas_dia['horas_recargo_nocturno']
            
            if data['liquida_dominical']:
                horas['dominical'] += horas_dia['horas_dominical']
            
            # Detalle del día
            if horas_dia['intervalos']:
                detalle_dias.append({
                    'fecha': fecha_str,
                    'entrada': horas_dia['intervalos'][0]['entrada'] if horas_dia['intervalos'] else None,
                    'salida': horas_dia['intervalos'][-1]['salida'] if horas_dia['intervalos'] else None,
                    'horas': horas_dia['horas_trabajadas']
                })
        
        # Redondear horas
        for key in horas:
            horas[key] = round(horas[key], 2)
        
        # Calcular valores monetarios
        horas_para_calculo = {
            'horas_ordinarias': horas['ordinarias'],
            'horas_extra_diurna': horas['extra_diurna'],
            'horas_extra_nocturna': horas['extra_nocturna'],
            'horas_recargo_nocturno': horas['recargo_nocturno'],
            'horas_dominical': horas['dominical'],
            'es_domingo': False  # Se calcula por día
        }
        valores = calcular_valor_horas(horas_para_calculo, config)
        
        reportes.append({
            'empleado_id': emp_id,
            'codigo': data['codigo'],
            'nombre': data['nombre'],
            'cargo': data['cargo'],
            'departamento': data['departamento'],
            'dias_trabajados': len(data['registros_por_fecha']),
            'horas': horas,
            'valores': valores,
            'detalle_dias': detalle_dias
        })
    
    return {
        'periodo': periodo,
        'quincena': quincena,
        'rango': {
            'inicio': str(inicio),
            'fin': str(fin)
        },
        'filtros': {
            'restaurante': restaurante
        },
        'total_empleados': len(reportes),
        'reportes': reportes
    }
