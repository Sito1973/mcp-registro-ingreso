"""Utilidades para manejo de fechas"""

from datetime import date, datetime, timedelta
import pytz
import os


def get_timezone():
    """Obtiene la zona horaria configurada"""
    tz_name = os.getenv("TIMEZONE", "America/Bogota")
    return pytz.timezone(tz_name)


def get_current_date() -> date:
    """Obtiene la fecha actual en la zona horaria configurada"""
    tz = get_timezone()
    return datetime.now(tz).date()


def get_current_datetime() -> datetime:
    """Obtiene fecha y hora actual en la zona horaria configurada"""
    tz = get_timezone()
    return datetime.now(tz)


def get_week_range(fecha: date = None) -> tuple[date, date]:
    """
    Obtiene el rango de fechas de la semana.
    
    Args:
        fecha: Fecha de referencia (default: hoy)
    
    Returns:
        Tupla con (inicio_semana, fin_semana)
    """
    if fecha is None:
        fecha = get_current_date()
    
    # Lunes = 0, Domingo = 6
    inicio = fecha - timedelta(days=fecha.weekday())
    fin = inicio + timedelta(days=6)
    
    return inicio, fin


def get_month_range(anio: int, mes: int) -> tuple[date, date]:
    """
    Obtiene el rango de fechas de un mes.
    
    Args:
        anio: Año
        mes: Mes (1-12)
    
    Returns:
        Tupla con (inicio_mes, fin_mes)
    """
    inicio = date(anio, mes, 1)
    
    # Obtener último día del mes
    if mes == 12:
        fin = date(anio + 1, 1, 1) - timedelta(days=1)
    else:
        fin = date(anio, mes + 1, 1) - timedelta(days=1)
    
    return inicio, fin


def get_quincena_range(anio: int, mes: int, quincena: int) -> tuple[date, date]:
    """
    Obtiene el rango de fechas de una quincena.
    
    Args:
        anio: Año
        mes: Mes (1-12)
        quincena: 1 (días 1-15) o 2 (días 16-fin)
    
    Returns:
        Tupla con (inicio, fin)
    """
    if quincena == 1:
        inicio = date(anio, mes, 1)
        fin = date(anio, mes, 15)
    else:
        inicio = date(anio, mes, 16)
        # Último día del mes
        if mes == 12:
            fin = date(anio + 1, 1, 1) - timedelta(days=1)
        else:
            fin = date(anio, mes + 1, 1) - timedelta(days=1)
    
    return inicio, fin


def format_date(fecha: date) -> str:
    """Formatea una fecha a string legible"""
    meses = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    return f"{fecha.day} de {meses[fecha.month]} de {fecha.year}"
