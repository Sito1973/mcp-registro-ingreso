"""Utilidades de cálculo de horas laborales según normativa colombiana"""

from datetime import datetime, time, date, timedelta
from typing import List, Dict

# Constantes laborales Colombia
HORA_INICIO_NOCTURNO = time(21, 0)  # 9:00 PM
HORA_FIN_NOCTURNO = time(6, 0)      # 6:00 AM
JORNADA_ORDINARIA = 8               # horas
LIMITE_SEMANAL = 48                 # horas

# Factores de recargo
FACTOR_EXTRA_DIURNA = 1.25          # +25%
FACTOR_EXTRA_NOCTURNA = 1.75        # +75%
FACTOR_RECARGO_NOCTURNO = 0.35      # +35%
FACTOR_DOMINICAL = 1.75             # +75%
FACTOR_EXTRA_DOMINICAL_DIURNA = 2.0    # +100%
FACTOR_EXTRA_DOMINICAL_NOCTURNA = 2.5  # +150%


def es_hora_nocturna(hora: time) -> bool:
    """Determina si una hora está en franja nocturna (21:00 - 06:00)"""
    return hora >= HORA_INICIO_NOCTURNO or hora < HORA_FIN_NOCTURNO


def calcular_diferencia_horas(inicio: time, fin: time) -> float:
    """Calcula diferencia en horas entre dos tiempos"""
    inicio_dt = datetime.combine(date.today(), inicio)
    fin_dt = datetime.combine(date.today(), fin)

    # Si fin es menor que inicio, asumimos que cruzó medianoche
    if fin < inicio:
        fin_dt += timedelta(days=1)

    diferencia = (fin_dt - inicio_dt).total_seconds() / 3600
    return round(diferencia, 2)


def calcular_horas_nocturnas(entrada: time, salida: time) -> float:
    """Calcula cuántas horas de un intervalo son nocturnas"""
    total_nocturnas = 0.0

    # Convertir a minutos desde medianoche para facilitar cálculos
    entrada_min = entrada.hour * 60 + entrada.minute
    salida_min = salida.hour * 60 + salida.minute

    # Si cruzó medianoche
    if salida_min < entrada_min:
        salida_min += 24 * 60

    # Franja nocturna: 21:00 (1260 min) a 06:00 (360 min)
    nocturno_inicio = 21 * 60  # 1260
    nocturno_fin = 6 * 60      # 360

    for minuto in range(entrada_min, salida_min):
        minuto_normalizado = minuto % (24 * 60)
        if minuto_normalizado >= nocturno_inicio or minuto_normalizado < nocturno_fin:
            total_nocturnas += 1/60

    return round(total_nocturnas, 2)


def calcular_horas_dia(registros: List[Dict], fecha: date) -> Dict:
    """
    Calcula todas las horas de un día con desglose completo.

    Args:
        registros: Lista de registros ordenados por hora
        fecha: Fecha del cálculo

    Returns:
        Diccionario con desglose de horas
    """
    intervalos = []
    horas_total = 0.0
    horas_nocturnas_total = 0.0

    # Determinar si es domingo (6 = domingo en weekday())
    es_domingo = fecha.weekday() == 6

    # Emparejar ENTRADA con siguiente SALIDA
    i = 0
    while i < len(registros):
        if registros[i]['tipo_registro'] == 'ENTRADA':
            entrada = registros[i]['hora_registro']

            # Buscar siguiente SALIDA
            for j in range(i + 1, len(registros)):
                if registros[j]['tipo_registro'] == 'SALIDA':
                    salida = registros[j]['hora_registro']

                    horas = calcular_diferencia_horas(entrada, salida)
                    horas_nocturnas = calcular_horas_nocturnas(entrada, salida)

                    intervalos.append({
                        'entrada': str(entrada),
                        'salida': str(salida),
                        'horas': horas,
                        'horas_nocturnas': horas_nocturnas,
                        'horas_diurnas': round(horas - horas_nocturnas, 2)
                    })

                    horas_total += horas
                    horas_nocturnas_total += horas_nocturnas
                    i = j
                    break
        i += 1

    # Calcular desglose
    horas_diurnas_total = round(horas_total - horas_nocturnas_total, 2)

    # Horas ordinarias vs extras
    horas_ordinarias = min(horas_total, JORNADA_ORDINARIA)
    horas_extra = max(0, horas_total - JORNADA_ORDINARIA)

    # Distribuir extras entre diurnas y nocturnas
    if horas_extra > 0:
        proporcion_nocturna = horas_nocturnas_total / horas_total if horas_total > 0 else 0
        horas_extra_nocturna = round(horas_extra * proporcion_nocturna, 2)
        horas_extra_diurna = round(horas_extra - horas_extra_nocturna, 2)
    else:
        horas_extra_diurna = 0
        horas_extra_nocturna = 0

    return {
        'fecha': str(fecha),
        'es_domingo': es_domingo,
        'horas_trabajadas': round(horas_total, 2),
        'horas_ordinarias': round(horas_ordinarias, 2),
        'horas_extra_diurna': horas_extra_diurna,
        'horas_extra_nocturna': horas_extra_nocturna,
        'horas_recargo_nocturno': round(horas_nocturnas_total, 2),
        'horas_dominical': round(horas_total, 2) if es_domingo else 0,
        'intervalos': intervalos,
        'total_intervalos': len(intervalos)
    }


def calcular_valor_horas(horas: Dict, config: Dict) -> Dict:
    """
    Calcula el valor monetario de las horas trabajadas.

    Args:
        horas: Diccionario con desglose de horas
        config: Configuración con valores hora

    Returns:
        Diccionario con valores calculados
    """
    valor_ordinaria = float(config.get('valor_hora_ordinaria', 5833.33))
    valor_extra_diurna = float(config.get('valor_hora_extra_diurna', valor_ordinaria * FACTOR_EXTRA_DIURNA))
    valor_extra_nocturna = float(config.get('valor_hora_extra_nocturna', valor_ordinaria * FACTOR_EXTRA_NOCTURNA))

    valores = {
        'ordinarias': round(horas['horas_ordinarias'] * valor_ordinaria, 2),
        'extra_diurna': round(horas['horas_extra_diurna'] * valor_extra_diurna, 2),
        'extra_nocturna': round(horas['horas_extra_nocturna'] * valor_extra_nocturna, 2),
        'recargo_nocturno': round(horas['horas_recargo_nocturno'] * valor_ordinaria * FACTOR_RECARGO_NOCTURNO, 2),
    }

    if horas.get('es_domingo'):
        valores['dominical'] = round(horas['horas_dominical'] * valor_ordinaria * FACTOR_DOMINICAL, 2)
    else:
        valores['dominical'] = 0

    valores['total'] = sum(valores.values())

    return valores
