"""Herramientas MCP para consulta de empleados"""

from typing import Optional


async def consultar_empleados(
    db,
    activos_solo: bool = True,
    restaurante: Optional[str] = None,
    departamento: Optional[str] = None
) -> list[dict]:
    """
    Lista empleados del sistema con filtros opcionales.

    Args:
        db: Instancia de Database
        activos_solo: Solo empleados activos (default: True)
        restaurante: Filtrar por punto de trabajo
        departamento: Filtrar por departamento

    Returns:
        Lista de empleados
    """
    query = """
        SELECT
            id,
            codigo_empleado,
            nombre,
            apellido,
            email,
            telefono,
            departamento,
            cargo,
            liquida_dominical,
            dia_descanso,
            punto_trabajo,
            activo,
            created_at
        FROM empleados
        WHERE (:activo = FALSE OR activo = :activo)
          AND (:restaurante IS NULL OR punto_trabajo = :restaurante)
          AND (:departamento IS NULL OR departamento = :departamento)
        ORDER BY apellido, nombre
    """
    
    params = {
        'activo': activos_solo,
        'restaurante': restaurante,
        'departamento': departamento
    }
    
    results = await db.execute(query, params)
    
    # Formatear resultados
    empleados = []
    for row in results:
        empleados.append({
            'id': str(row['id']),
            'codigo_empleado': row['codigo_empleado'],
            'nombre_completo': f"{row['nombre']} {row['apellido']}",
            'nombre': row['nombre'],
            'apellido': row['apellido'],
            'email': row['email'],
            'telefono': row['telefono'],
            'departamento': row['departamento'],
            'cargo': row['cargo'],
            'punto_trabajo': row['punto_trabajo'],
            'liquida_dominical': row['liquida_dominical'],
            'dia_descanso': row['dia_descanso'],
            'activo': row['activo']
        })
    
    return {
        'total': len(empleados),
        'filtros': {
            'activos_solo': activos_solo,
            'restaurante': restaurante,
            'departamento': departamento
        },
        'empleados': empleados
    }


async def buscar_empleado(db, termino: str) -> list[dict]:
    """
    Busca empleados por código, nombre o apellido.

    Args:
        db: Instancia de Database
        termino: Texto a buscar

    Returns:
        Lista de empleados que coinciden
    """
    query = """
        SELECT
            id,
            codigo_empleado,
            nombre,
            apellido,
            cargo,
            departamento,
            punto_trabajo,
            activo
        FROM empleados
        WHERE codigo_empleado ILIKE '%' || :termino || '%'
           OR nombre ILIKE '%' || :termino || '%'
           OR apellido ILIKE '%' || :termino || '%'
        ORDER BY
            CASE WHEN codigo_empleado ILIKE :termino THEN 0 ELSE 1 END,
            apellido, nombre
        LIMIT 20
    """
    
    results = await db.execute(query, {'termino': termino})
    
    empleados = []
    for row in results:
        empleados.append({
            'id': str(row['id']),
            'codigo_empleado': row['codigo_empleado'],
            'nombre_completo': f"{row['nombre']} {row['apellido']}",
            'cargo': row['cargo'],
            'departamento': row['departamento'],
            'punto_trabajo': row['punto_trabajo'],
            'activo': row['activo']
        })
    
    return {
        'termino_busqueda': termino,
        'resultados': len(empleados),
        'empleados': empleados
    }
