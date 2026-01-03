"""MCP Server for Odoo Analytics"""

import os
import asyncio
from datetime import datetime, date, timedelta
from typing import Any
from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .odoo_client import OdooClient
from . import pos_tools

# Load environment variables
load_dotenv()

# Initialize MCP server
app = Server("odoo-analytics")

# Odoo connection configuration
ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "cocson_2025")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

if not ODOO_PASSWORD:
    raise ValueError("ODOO_PASSWORD environment variable is required")


def get_odoo_client() -> OdooClient:
    """Get authenticated Odoo client"""
    client = OdooClient(ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
    client.authenticate()
    return client


def utc_to_bogota(utc_datetime_str: str) -> str:
    """
    Convert Odoo UTC datetime string to Bogotá local time (UTC-5)
    Use this for all date displays to show correct local time.
    """
    if not utc_datetime_str:
        return ''
    try:
        utc_dt = datetime.strptime(utc_datetime_str, '%Y-%m-%d %H:%M:%S')
        bogota_dt = utc_dt - timedelta(hours=5)
        return bogota_dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return utc_datetime_str


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        # Server/System tools
        Tool(
            name="get_server_datetime",
            description="Obtiene la fecha y hora actual del servidor Odoo, incluyendo zona horaria y información del servidor",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_sales_today",
            description="Obtiene el resumen de ventas del día actual (POS y Sale Orders)",
            inputSchema={
                "type": "object",
                "properties": {
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional, ej: 'sumo', 'bandidos')"
                    }
                }
            }
        ),
        Tool(
            name="get_sales_by_date",
            description="Obtiene ventas de una fecha específica",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha en formato YYYY-MM-DD"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date"]
            }
        ),
        Tool(
            name="get_sales_by_period",
            description="Obtiene ventas en un período de fechas",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicial (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha final (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="get_top_cashiers",
            description="Obtiene ranking de cajeros por ventas",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha específica (YYYY-MM-DD) o 'today'"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Número de cajeros a retornar (default: 10)"
                    }
                },
                "required": ["date"]
            }
        ),
        Tool(
            name="get_top_products",
            description="Obtiene los productos más vendidos",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicial (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha final (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional, ej: 'bandidos', 'leños')"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Número de productos a retornar (default: 20)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="get_sales_by_payment_method",
            description="Obtiene ventas agrupadas por método de pago",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha específica (YYYY-MM-DD) o 'today'"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date"]
            }
        ),
        # POS-specific tools
        Tool(
            name="get_top_products_by_cashier",
            description="Obtiene ranking de productos más vendidos por cada cajero",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha específica (YYYY-MM-DD) o 'today'"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Número de productos por cajero (default: 10)"
                    }
                },
                "required": ["date"]
            }
        ),
        Tool(
            name="get_sales_by_customer_type",
            description="Obtiene ventas agrupadas por tipo de cliente (empresas vs consumidor final)",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha específica (YYYY-MM-DD) o 'today'"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date"]
            }
        ),
        Tool(
            name="get_top_customers",
            description="Obtiene los mejores clientes por volumen de ventas",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicial (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha final (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Número de clientes (default: 20)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="get_sales_by_table",
            description="Obtiene ventas por mesa/piso (POS Restaurant)",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha específica (YYYY-MM-DD) o 'today'"
                    },
                    "floor_name": {
                        "type": "string",
                        "description": "Filtrar por piso/área (opcional)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Número de mesas (default: 20)"
                    }
                },
                "required": ["date"]
            }
        ),

        Tool(
            name="get_open_sessions",
            description="Obtiene todas las sesiones POS actualmente abiertas",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        # New advanced tools
        Tool(
            name="get_sales_by_employee",
            description="Obtiene ventas filtradas por un empleado/cajero específico",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha específica (YYYY-MM-DD) o 'today'"
                    },
                    "employee_name": {
                        "type": "string",
                        "description": "Nombre del empleado/cajero a filtrar"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date", "employee_name"]
            }
        ),
        Tool(
            name="get_hourly_sales",
            description="Obtiene ventas agrupadas por hora del día (análisis de picos)",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha específica (YYYY-MM-DD) o 'today'"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date"]
            }
        ),
        Tool(
            name="get_canceled_orders",
            description="Obtiene órdenes canceladas/devueltas por fecha",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha específica (YYYY-MM-DD) o 'today'"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date"]
            }
        ),
        Tool(
            name="get_discounts_applied",
            description="Obtiene descuentos aplicados por cajero/producto",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha específica (YYYY-MM-DD) o 'today'"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date"]
            }
        ),
        # New advanced analytics tools
        Tool(
            name="get_orders_by_time_range",
            description="Obtiene órdenes en un rango horario específico (ej: almuerzo 12-15h)",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha específica (YYYY-MM-DD) o 'today'"
                    },
                    "hour_start": {
                        "type": "number",
                        "description": "Hora inicio (0-23, ej: 12)"
                    },
                    "hour_end": {
                        "type": "number",
                        "description": "Hora fin (0-23, ej: 15)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date", "hour_start", "hour_end"]
            }
        ),
        Tool(
            name="compare_periods",
            description="Compara ventas entre dos períodos (ej: esta semana vs semana anterior)",
            inputSchema={
                "type": "object",
                "properties": {
                    "period1_start": {
                        "type": "string",
                        "description": "Inicio período 1 (YYYY-MM-DD)"
                    },
                    "period1_end": {
                        "type": "string",
                        "description": "Fin período 1 (YYYY-MM-DD)"
                    },
                    "period2_start": {
                        "type": "string",
                        "description": "Inicio período 2 (YYYY-MM-DD)"
                    },
                    "period2_end": {
                        "type": "string",
                        "description": "Fin período 2 (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["period1_start", "period1_end", "period2_start", "period2_end"]
            }
        ),
        Tool(
            name="get_product_categories_sales",
            description="Obtiene ventas agrupadas por categoría de producto",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicial (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha final (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="get_sales_by_partner",
            description="Obtiene ventas filtradas por cliente/empresa específica",
            inputSchema={
                "type": "object",
                "properties": {
                    "partner_name": {
                        "type": "string",
                        "description": "Nombre del cliente/empresa"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicial (YYYY-MM-DD, opcional)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha final (YYYY-MM-DD, opcional)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["partner_name"]
            }
        ),
        Tool(
            name="get_partner_order_history",
            description="Obtiene historial completo de órdenes de un cliente",
            inputSchema={
                "type": "object",
                "properties": {
                    "partner_name": {
                        "type": "string",
                        "description": "Nombre del cliente/empresa"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Número máximo de órdenes (default: 50)"
                    }
                },
                "required": ["partner_name"]
            }
        ),
        # Product management tools
        Tool(
            name="get_product_details",
            description="Obtiene información completa de un producto",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Nombre o código del producto"
                    }
                },
                "required": ["product_name"]
            }
        ),
        Tool(
            name="search_products",
            description="Busca productos por nombre, código o categoría",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Término de búsqueda"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filtrar por categoría (opcional)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Número máximo de resultados (default: 20)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_product_categories",
            description="Lista todas las categorías/secciones de productos disponibles",
            inputSchema={
                "type": "object",
                "properties": {
                    "parent_category": {
                        "type": "string",
                        "description": "Filtrar por categoría padre (opcional)"
                    }
                }
            }
        ),
        Tool(
            name="get_products_by_category",
            description="Lista todos los productos de una categoría/sección específica",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Nombre de la categoría/sección"
                    },
                    "include_subcategories": {
                        "type": "boolean",
                        "description": "Incluir productos de subcategorías (default: true)"
                    },
                    "only_available": {
                        "type": "boolean",
                        "description": "Solo productos disponibles en POS (default: true)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Número máximo de productos (default: 50)"
                    }
                },
                "required": ["category"]
            }
        ),
        Tool(
            name="update_product_price",
            description="Actualiza el precio de venta de un producto (⚠️ modifica datos)",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "Nombre exacto del producto"
                    },
                    "new_price": {
                        "type": "number",
                        "description": "Nuevo precio de venta"
                    }
                },
                "required": ["product_name", "new_price"]
            }
        ),
        # Employee performance tools
        Tool(
            name="get_employee_performance",
            description="Obtiene métricas de rendimiento de un empleado específico",
            inputSchema={
                "type": "object",
                "properties": {
                    "employee_name": {
                        "type": "string",
                        "description": "Nombre del empleado"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicial (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha final (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["employee_name", "date_from", "date_to"]
            }
        ),
        Tool(
            name="get_best_employee_by_metric",
            description="Obtiene el mejor empleado según una métrica específica",
            inputSchema={
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "Métrica: 'ventas', 'ordenes', 'ticket_promedio', 'productos'"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicial (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha final (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Número de empleados a mostrar (default: 10)"
                    }
                },
                "required": ["metric", "date_from", "date_to"]
            }
        ),
        # POS Order Reports
        Tool(
            name="get_order_details",
            description="Obtiene el detalle completo de una orden específica (incluyendo productos y pagos)",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_name": {
                        "type": "string",
                        "description": "Nombre o referencia de la orden (ej: 'POST/2023/12/0001')"
                    }
                },
                "required": ["order_name"]
            }
        ),
        Tool(
            name="search_orders",
            description="Busca órdenes en el POS por número, cliente o monto",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Número de orden o nombre del cliente"
                    },
                    "min_amount": {
                        "type": "number",
                        "description": "Monto mínimo"
                    },
                    "max_amount": {
                        "type": "number",
                        "description": "Monto máximo"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Máximo de resultados (default: 20)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_daily_summary",
            description="Genera un resumen ejecutivo de las ventas de un día específico",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha (YYYY-MM-DD) o 'today'"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date"]
            }
        ),
        Tool(
            name="get_most_frequent_customers",
            description="Muestra los clientes con mayor frecuencia de compra en un período",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicio (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha fin (YYYY-MM-DD)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Número de clientes (default: 10)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="get_sales_by_weekday",
            description="Analiza las ventas agregadas por día de la semana",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicio (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha fin (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="get_peak_hours_analysis",
            description="Analiza las horas de mayor actividad comercial en un rango de fechas",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicio (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha fin (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="get_month_over_month",
            description="Analiza el rendimiento mensual comparado con el mes anterior",
            inputSchema={
                "type": "object",
                "properties": {
                    "month": {
                        "type": "number",
                        "description": "Mes a analizar (1-12)"
                    },
                    "year": {
                        "type": "number",
                        "description": "Año a analizar"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["month", "year"]
            }
        ),
        Tool(
            name="get_growth_trends",
            description="Analiza las tendencias de crecimiento semanal o mensual",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "Tipo de período: 'semanal' o 'mensual'"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Número de períodos hacia atrás (default: 4)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["period"]
            }
        ),
        # Restaurant specific tools
        Tool(
            name="get_restaurant_layout",
            description="Muestra la distribución del restaurante (pisos y mesas)",
            inputSchema={
                "type": "object",
                "properties": {
                    "floor_name": {
                        "type": "string",
                        "description": "Filtrar por piso (opcional)"
                    }
                }
            }
        ),
        Tool(
            name="get_guest_metrics",
            description="Obtiene métricas de comensales (ocupación, gasto por persona)",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicio (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha fin (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="get_kitchen_stats",
            description="Estadísticas de cocina: productos más pedidos por hora del día",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicio (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha fin (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="get_tips_summary",
            description="Resumen de propinas por empleado en un período",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicio (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha fin (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="get_low_stock_products",
            description="Obtiene productos con stock bajo (disponibles en POS)",
            inputSchema={
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "number",
                        "description": "Umbral de stock mínimo (default: 10)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filtrar por categoría (opcional)"
                    }
                }
            }
        ),
        Tool(
            name="get_invoices_summary",
            description="Resumen de facturas emitidas en un período",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicio (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha fin (YYYY-MM-DD)"
                    },
                    "state": {
                        "type": "string",
                        "description": "Estado: draft, posted, cancel (opcional)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        Tool(
            name="get_invoice_details",
            description="Obtener detalles completos de una factura específica",
            inputSchema={
                "type": "object",
                "properties": {
                    "invoice_number": {
                        "type": "string",
                        "description": "Número de factura (ej: INV/2025/00001)"
                    },
                    "invoice_id": {
                        "type": "integer",
                        "description": "ID de la factura (opcional si se da número)"
                    }
                }
            }
        ),
        Tool(
            name="search_invoices",
            description="Buscar facturas por cliente, número o referencia",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Término de búsqueda (cliente, número, referencia)"
                    },
                    "state": {
                        "type": "string",
                        "description": "Estado: draft, posted, cancel (opcional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Límite de resultados (default: 20)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_customer_invoices",
            description="Obtener todas las facturas de un cliente específico",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Nombre del cliente o empresa"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicio (YYYY-MM-DD, opcional)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha fin (YYYY-MM-DD, opcional)"
                    },
                    "include_paid": {
                        "type": "boolean",
                        "description": "Incluir facturas pagadas (default: true)"
                    }
                },
                "required": ["customer_name"]
            }
        ),
        Tool(
            name="get_session_reconciliation",
            description="Cuadre de caja de sesiones POS (diferencias)",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_name": {
                        "type": "string",
                        "description": "Nombre de sesión específica (opcional)"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicio (YYYY-MM-DD, opcional)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha fin (YYYY-MM-DD, opcional)"
                    }
                }
            }
        ),
        Tool(
            name="get_session_details",
            description="Obtener detalles completos de una sesión POS",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "integer",
                        "description": "ID de la sesión (opcional si se da nombre)"
                    },
                    "session_name": {
                        "type": "string",
                        "description": "Nombre de la sesión (ej: POS/1234)"
                    }
                }
            }
        ),
        Tool(
            name="get_sessions_by_cashier",
            description="Historial de sesiones por cajero/usuario",
            inputSchema={
                "type": "object",
                "properties": {
                    "cashier_name": {
                        "type": "string",
                        "description": "Nombre del cajero o usuario"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Límite de resultados (default: 10)"
                    }
                },
                "required": ["cashier_name"]
            }
        ),
        Tool(
            name="get_session_vs_session",
            description="Comparar rendimiento entre dos sesiones POS",
            inputSchema={
                "type": "object",
                "properties": {
                    "session1_name": {
                        "type": "string",
                        "description": "Nombre o ID de la primera sesión"
                    },
                    "session2_name": {
                        "type": "string",
                        "description": "Nombre o ID de la segunda sesión"
                    }
                },
                "required": ["session1_name", "session2_name"]
            }
        ),
        Tool(
            name="get_busiest_sessions",
            description="Top sesiones con más ventas u órdenes",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicio (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha fin (YYYY-MM-DD)"
                    },
                    "metric": {
                        "type": "string",
                        "description": "Métrica: amount (ventas) o orders (órdenes)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Límite de resultados (default: 5)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        ),
        # Employee products sold tool
        Tool(
            name="get_employee_products_sold",
            description="Obtiene los productos vendidos por un empleado específico con detalle de cantidades y montos",
            inputSchema={
                "type": "object",
                "properties": {
                    "employee_name": {
                        "type": "string",
                        "description": "Nombre del empleado/cajero"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Fecha inicial (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Fecha final (YYYY-MM-DD)"
                    },
                    "pos_config": {
                        "type": "string",
                        "description": "Filtrar por punto de venta (opcional)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Número de productos a mostrar (default: 30)"
                    }
                },
                "required": ["employee_name", "date_from", "date_to"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""

    try:
        # Server/System tools
        if name == "get_server_datetime":
            result = await get_server_datetime()
        elif name == "get_sales_today":
            result = await get_sales_today(arguments.get("pos_config"))
        elif name == "get_sales_by_date":
            result = await get_sales_by_date(
                arguments["date"],
                arguments.get("pos_config")
            )
        elif name == "get_sales_by_period":
            result = await get_sales_by_period(
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("pos_config")
            )
        elif name == "get_top_cashiers":
            result = await get_top_cashiers(
                arguments["date"],
                arguments.get("pos_config"),
                arguments.get("limit", 10)
            )
        elif name == "get_top_products":
            result = await get_top_products(
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("pos_config"),
                arguments.get("limit", 20)
            )
        elif name == "get_sales_by_payment_method":
            result = await get_sales_by_payment_method(
                arguments["date"],
                arguments.get("pos_config")
            )
        # POS-specific tools
        elif name == "get_top_products_by_cashier":
            client = get_odoo_client()
            result = await pos_tools.get_top_products_by_cashier(
                arguments["date"],
                arguments.get("pos_config"),
                arguments.get("limit", 10),
                client
            )
        elif name == "get_sales_by_customer_type":
            client = get_odoo_client()
            result = await pos_tools.get_sales_by_customer_type(
                arguments["date"],
                arguments.get("pos_config"),
                client
            )
        elif name == "get_top_customers":
            client = get_odoo_client()
            result = await pos_tools.get_top_customers(
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("pos_config"),
                arguments.get("limit", 20),
                client
            )
        elif name == "get_sales_by_table":
            client = get_odoo_client()
            result = await pos_tools.get_sales_by_table(
                arguments["date"],
                arguments.get("floor_name"),
                arguments.get("limit", 20),
                client
            )
        elif name == "get_session_details":
            client = get_odoo_client()
            result = await pos_tools.get_session_details(
                arguments["session_id"],
                client
            )
        elif name == "get_open_sessions":
            client = get_odoo_client()
            result = await pos_tools.get_open_sessions(client)
        # New advanced tools
        elif name == "get_sales_by_employee":
            result = await get_sales_by_employee(
                arguments["date"],
                arguments["employee_name"],
                arguments.get("pos_config")
            )
        elif name == "get_hourly_sales":
            result = await get_hourly_sales(
                arguments["date"],
                arguments.get("pos_config")
            )
        elif name == "get_canceled_orders":
            result = await get_canceled_orders(
                arguments["date"],
                arguments.get("pos_config")
            )
        elif name == "get_discounts_applied":
            result = await get_discounts_applied(
                arguments["date"],
                arguments.get("pos_config")
            )
        # New advanced analytics tools
        elif name == "get_orders_by_time_range":
            result = await get_orders_by_time_range(
                arguments["date"],
                arguments["hour_start"],
                arguments["hour_end"],
                arguments.get("pos_config")
            )
        elif name == "compare_periods":
            result = await compare_periods(
                arguments["period1_start"],
                arguments["period1_end"],
                arguments["period2_start"],
                arguments["period2_end"],
                arguments.get("pos_config")
            )
        elif name == "get_product_categories_sales":
            result = await get_product_categories_sales(
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("pos_config")
            )
        elif name == "get_sales_by_partner":
            result = await get_sales_by_partner(
                arguments["partner_name"],
                arguments.get("date_from"),
                arguments.get("date_to"),
                arguments.get("pos_config")
            )
        elif name == "get_partner_order_history":
            result = await get_partner_order_history(
                arguments["partner_name"],
                arguments.get("limit", 50)
            )
        # Product management tools
        elif name == "get_product_details":
            result = await get_product_details(
                arguments["product_name"]
            )
        elif name == "search_products":
            result = await search_products(
                arguments["query"],
                arguments.get("category"),
                arguments.get("limit", 20)
            )
        elif name == "get_product_categories":
            result = await get_product_categories(
                arguments.get("parent_category")
            )
        elif name == "get_products_by_category":
            result = await get_products_by_category(
                arguments["category"],
                arguments.get("include_subcategories", True),
                arguments.get("only_available", True),
                arguments.get("limit", 50)
            )
        elif name == "update_product_price":
            result = await update_product_price(
                arguments["product_name"],
                arguments["new_price"]
            )
        # Employee performance tools
        elif name == "get_employee_performance":
            result = await get_employee_performance(
                arguments["employee_name"],
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("pos_config")
            )
        elif name == "get_best_employee_by_metric":
            result = await get_best_employee_by_metric(
                arguments["metric"],
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("pos_config"),
                arguments.get("limit", 10)
            )
        elif name == "get_employee_products_sold":
            result = await get_employee_products_sold(
                arguments["employee_name"],
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("pos_config"),
                arguments.get("limit", 30)
            )
        # POS Order Reports
        elif name == "get_order_details":
            result = await get_order_details(
                arguments["order_name"]
            )
        elif name == "search_orders":
            result = await search_orders(
                arguments["query"],
                arguments.get("min_amount"),
                arguments.get("max_amount"),
                arguments.get("limit", 20)
            )
        elif name == "get_daily_summary":
            result = await get_daily_summary(
                arguments["date"],
                arguments.get("pos_config")
            )
        elif name == "get_most_frequent_customers":
            result = await get_most_frequent_customers(
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("limit", 10)
            )
        elif name == "get_sales_by_weekday":
            result = await get_sales_by_weekday(
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("pos_config")
            )
        elif name == "get_peak_hours_analysis":
            result = await get_peak_hours_analysis(
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("pos_config")
            )
        elif name == "get_month_over_month":
            result = await get_month_over_month(
                arguments["month"],
                arguments["year"],
                arguments.get("pos_config")
            )
        elif name == "get_growth_trends":
            result = await get_growth_trends(
                arguments["period"],
                arguments.get("limit", 4),
                arguments.get("pos_config")
            )
        elif name == "get_session_details":
            result = await get_session_details(
                arguments.get("session_id"),
                arguments.get("session_name")
            )
        elif name == "get_sessions_by_cashier":
            result = await get_sessions_by_cashier(
                arguments["cashier_name"],
                arguments.get("limit", 10)
            )
        elif name == "get_session_vs_session":
            result = await get_session_vs_session(
                arguments["session1_name"],
                arguments["session2_name"]
            )
        elif name == "get_busiest_sessions":
            result = await get_busiest_sessions(
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("metric", "amount"),
                arguments.get("limit", 5)
            )
        # Restaurant specific tools
        elif name == "get_restaurant_layout":
            result = await get_restaurant_layout(
                arguments.get("floor_name")
            )
        elif name == "get_guest_metrics":
            result = await get_guest_metrics(
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("pos_config")
            )
        elif name == "get_kitchen_stats":
            result = await get_kitchen_stats(
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("pos_config")
            )
        elif name == "get_tips_summary":
            result = await get_tips_summary(
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("pos_config")
            )
        elif name == "get_low_stock_products":
            result = await get_low_stock_products(
                arguments.get("threshold", 10),
                arguments.get("category")
            )
        elif name == "get_invoices_summary":
            result = await get_invoices_summary(
                arguments["date_from"],
                arguments["date_to"],
                arguments.get("state")
            )
        elif name == "get_session_reconciliation":
            result = await get_session_reconciliation(
                arguments.get("session_name"),
                arguments.get("date_from"),
                arguments.get("date_to")
            )
        elif name == "get_invoice_details":
            result = await get_invoice_details(
                arguments.get("invoice_number"),
                arguments.get("invoice_id")
            )
        elif name == "search_invoices":
            result = await search_invoices(
                arguments["query"],
                arguments.get("state"),
                arguments.get("limit", 20)
            )
        elif name == "get_customer_invoices":
            result = await get_customer_invoices(
                arguments["customer_name"],
                arguments.get("date_from"),
                arguments.get("date_to"),
                arguments.get("include_paid", True)
            )
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=result)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# SERVER/SYSTEM TOOLS
# ============================================================================

async def get_server_datetime() -> str:
    """Get current date and time from Odoo server"""

    client = get_odoo_client()

    # Get server info using ir.config_parameter
    try:
        # Get database info
        db_name = ODOO_DB

        # Get current datetime from server by reading a record's write_date
        # This ensures we get the server's timezone
        server_info = client.execute(
            'ir.config_parameter',
            'search_read',
            [('key', '=', 'database.create_date')],
            ['value']
        )

        # Get company info for timezone
        company = client.search_read(
            'res.company',
            [('id', '=', 1)],
            ['name', 'currency_id']
        )

        company_name = company[0]['name'] if company else 'N/A'
        currency = company[0]['currency_id'][1] if company and company[0].get('currency_id') else 'N/A'

        # Get current server time by checking a recent record
        # We use res.users as it's always available
        users = client.search_read(
            'res.users',
            [('id', '=', client._uid)],
            ['login', 'write_date', 'tz']
        )

        user_tz = users[0].get('tz', 'UTC') if users else 'UTC'
        server_write_date = users[0].get('write_date', '') if users else ''

        # Get current datetime (local)
        now_local = datetime.now()
        now_utc = datetime.utcnow()

        # Count active POS sessions
        open_sessions = client.search_read(
            'pos.session',
            [('state', '=', 'opened')],
            ['name', 'user_id', 'config_id']
        )

        result = f"""
{'='*60}
INFORMACION DEL SERVIDOR ODOO
{'='*60}

Fecha y Hora Local:    {now_local.strftime('%Y-%m-%d %H:%M:%S')}
Fecha y Hora UTC:      {now_utc.strftime('%Y-%m-%d %H:%M:%S')}
Dia de la semana:      {now_local.strftime('%A')}

{'-'*60}
CONFIGURACION DEL SERVIDOR
{'-'*60}

Base de datos:         {db_name}
Empresa:               {company_name}
Moneda:                {currency}
Zona horaria usuario:  {user_tz}
URL del servidor:      {ODOO_URL}

{'-'*60}
ESTADO DEL POS
{'-'*60}

Sesiones POS abiertas: {len(open_sessions)}
"""

        if open_sessions:
            result += "\nSesiones activas:\n"
            for session in open_sessions:
                user_name = session['user_id'][1] if session['user_id'] else 'N/A'
                config_name = session['config_id'][1] if session['config_id'] else 'N/A'
                result += f"  - {session['name']} ({config_name}) - {user_name}\n"

        result += f"""
{'='*60}
"""

        return result

    except Exception as e:
        return f"Error al obtener informacion del servidor: {str(e)}"


async def get_sales_today(pos_config: str | None = None) -> str:
    """Get today's sales"""
    today = date.today()
    return await get_sales_by_date(today.strftime("%Y-%m-%d"), pos_config)


async def get_sales_by_date(date_str: str, pos_config: str | None = None) -> str:
    """Get sales for a specific date"""

    client = get_odoo_client()
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    date_start = datetime.combine(target_date, datetime.min.time())
    date_end = datetime.combine(target_date, datetime.max.time())

    # Build domain
    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(date_start)),
        ('date_order', '<=', client.datetime_to_odoo_format(date_end)),
        ('state', 'in', ['paid', 'done', 'invoiced'])
    ]

    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))

    # Get POS orders
    pos_orders = client.search_read(
        'pos.order',
        domain,
        ['name', 'date_order', 'amount_total', 'partner_id', 'employee_id', 'config_id']
    )

    if not pos_orders:
        return f"No se encontraron ventas para {date_str}"

    total = sum(order['amount_total'] for order in pos_orders)

    # Format result
    result = f"""
{'='*70}
VENTAS - {date_str}
{'='*70}

Total de órdenes: {len(pos_orders)}
Total vendido: ${total:,.2f}
Promedio por orden: ${total/len(pos_orders):,.2f}

{'='*70}

Detalle de órdenes:
{'-'*70}
"""

    for order in pos_orders:
        partner_name = order['partner_id'][1] if order['partner_id'] else 'CONSUMIDOR FINAL'
        result += f"{order['name']:20} | {partner_name:30} | ${order['amount_total']:>10,.2f}\n"

    return result


async def get_sales_by_period(date_from: str, date_to: str, pos_config: str | None = None) -> str:
    """Get sales for a period"""

    client = get_odoo_client()
    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())

    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('state', 'in', ['paid', 'done', 'invoiced'])
    ]

    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))

    pos_orders = client.search_read(
        'pos.order',
        domain,
        ['name', 'date_order', 'amount_total', 'config_id']
    )

    if not pos_orders:
        return f"No se encontraron ventas entre {date_from} y {date_to}"

    total = sum(order['amount_total'] for order in pos_orders)
    days = (dt_to.date() - dt_from.date()).days + 1

    result = f"""
{'='*70}
VENTAS - PERÍODO: {date_from} al {date_to}
{'='*70}

Total de órdenes: {len(pos_orders)}
Total vendido: ${total:,.2f}
Promedio por día: ${total/days:,.2f}
Promedio por orden: ${total/len(pos_orders):,.2f}

{'='*70}
"""

    return result


async def get_top_cashiers(date_str: str, pos_config: str | None = None, limit: int = 10) -> str:
    """Get top cashiers by sales"""

    client = get_odoo_client()

    if date_str.lower() == 'today':
        target_date = date.today()
    else:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    date_start = datetime.combine(target_date, datetime.min.time())
    date_end = datetime.combine(target_date, datetime.max.time())

    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(date_start)),
        ('date_order', '<=', client.datetime_to_odoo_format(date_end)),
        ('state', 'in', ['paid', 'done', 'invoiced'])
    ]

    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))

    pos_orders = client.search_read(
        'pos.order',
        domain,
        ['amount_total', 'employee_id']
    )

    if not pos_orders:
        return f"No se encontraron ventas para {date_str}"

    # Group by cashier
    cashiers = {}
    for order in pos_orders:
        if order['employee_id']:
            cashier_id = order['employee_id'][0]
            cashier_name = order['employee_id'][1]
        else:
            cashier_id = 0
            cashier_name = 'Sin cajero asignado'

        if cashier_id not in cashiers:
            cashiers[cashier_id] = {
                'name': cashier_name,
                'total': 0,
                'orders': 0
            }

        cashiers[cashier_id]['total'] += order['amount_total']
        cashiers[cashier_id]['orders'] += 1

    # Sort by total
    sorted_cashiers = sorted(cashiers.values(), key=lambda x: x['total'], reverse=True)[:limit]

    result = f"""
{'='*75}
RANKING DE CAJEROS - {date_str}
{'='*75}

{'Cajero':<35} | {'Órdenes':>8} | {'Total Ventas':>15}
{'-'*75}
"""

    for cashier in sorted_cashiers:
        result += f"{cashier['name']:<35} | {cashier['orders']:>8} | ${cashier['total']:>14,.2f}\n"

    if sorted_cashiers:
        top = sorted_cashiers[0]
        result += f"""
{'='*75}
🏆 TOP CAJERO: {top['name']}
   Órdenes: {top['orders']}
   Total: ${top['total']:,.2f}
   Promedio por orden: ${top['total']/top['orders']:,.2f}
{'='*75}
"""

    return result


async def get_top_products(date_from: str, date_to: str, pos_config: str | None = None, limit: int = 20) -> str:
    """Get top selling products"""

    client = get_odoo_client()
    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())

    # Get order lines
    domain = [
        ('order_id.date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('order_id.date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('order_id.state', 'in', ['paid', 'done', 'invoiced'])
    ]

    # Filter by POS config if provided
    if pos_config:
        domain.append(('order_id.config_id.name', 'ilike', pos_config))

    order_lines = client.search_read(
        'pos.order.line',
        domain,
        ['product_id', 'qty', 'price_subtotal_incl']
    )

    if not order_lines:
        return f"No se encontraron productos vendidos entre {date_from} y {date_to}"

    # Group by product
    products = {}
    for line in order_lines:
        product_id = line['product_id'][0]
        product_name = line['product_id'][1]

        if product_id not in products:
            products[product_id] = {
                'name': product_name,
                'qty': 0,
                'total': 0
            }

        products[product_id]['qty'] += line['qty']
        products[product_id]['total'] += line['price_subtotal_incl']

    # Sort by quantity
    sorted_products = sorted(products.values(), key=lambda x: x['qty'], reverse=True)[:limit]

    result = f"""
{'='*80}
TOP {limit} PRODUCTOS MÁS VENDIDOS - {date_from} al {date_to}
{'='*80}

{'Producto':<40} | {'Cantidad':>10} | {'Total':>15}
{'-'*80}
"""

    for product in sorted_products:
        result += f"{product['name'][:40]:<40} | {product['qty']:>10.0f} | ${product['total']:>14,.2f}\n"

    return result


async def get_sales_by_payment_method(date_str: str, pos_config: str | None = None) -> str:
    """Get sales grouped by payment method"""

    client = get_odoo_client()

    if date_str.lower() == 'today':
        target_date = date.today()
    else:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    date_start = datetime.combine(target_date, datetime.min.time())
    date_end = datetime.combine(target_date, datetime.max.time())

    domain = [
        ('payment_date', '>=', client.datetime_to_odoo_format(date_start)),
        ('payment_date', '<=', client.datetime_to_odoo_format(date_end)),
    ]

    if pos_config:
        domain.append(('session_id.config_id.name', 'ilike', pos_config))

    payments = client.search_read(
        'pos.payment',
        domain,
        ['payment_method_id', 'amount']
    )

    if not payments:
        return f"No se encontraron pagos para {date_str}"

    # Group by payment method
    methods = {}
    for payment in payments:
        method_id = payment['payment_method_id'][0]
        method_name = payment['payment_method_id'][1]

        if method_id not in methods:
            methods[method_id] = {
                'name': method_name,
                'total': 0,
                'count': 0
            }

        methods[method_id]['total'] += payment['amount']
        methods[method_id]['count'] += 1

    # Sort by total
    sorted_methods = sorted(methods.values(), key=lambda x: x['total'], reverse=True)

    total_all = sum(m['total'] for m in sorted_methods)

    result = f"""
{'='*75}
VENTAS POR MÉTODO DE PAGO - {date_str}
{'='*75}

{'Método de Pago':<30} | {'Transacciones':>12} | {'Total':>15} | {'%':>6}
{'-'*75}
"""

    for method in sorted_methods:
        percentage = (method['total'] / total_all * 100) if total_all > 0 else 0
        result += f"{method['name']:<30} | {method['count']:>12} | ${method['total']:>14,.2f} | {percentage:>5.1f}%\n"

    result += f"""
{'-'*75}
{'TOTAL':<30} | {sum(m['count'] for m in sorted_methods):>12} | ${total_all:>14,.2f} | 100.0%
{'='*75}
"""

    return result


# ============================================================================
# NEW ADVANCED TOOLS
# ============================================================================

async def get_sales_by_employee(date_str: str, employee_name: str, pos_config: str | None = None) -> str:
    """Get sales filtered by a specific employee/cashier"""

    client = get_odoo_client()

    if date_str.lower() == 'today':
        target_date = date.today()
    else:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    date_start = datetime.combine(target_date, datetime.min.time())
    date_end = datetime.combine(target_date, datetime.max.time())

    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(date_start)),
        ('date_order', '<=', client.datetime_to_odoo_format(date_end)),
        ('state', 'in', ['paid', 'done', 'invoiced']),
        ('employee_id.name', 'ilike', employee_name)
    ]

    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))

    pos_orders = client.search_read(
        'pos.order',
        domain,
        ['name', 'date_order', 'amount_total', 'partner_id', 'employee_id', 'config_id']
    )

    if not pos_orders:
        return f"No se encontraron ventas para el empleado '{employee_name}' en {date_str}"

    total = sum(order['amount_total'] for order in pos_orders)
    employee_found = pos_orders[0]['employee_id'][1] if pos_orders[0]['employee_id'] else employee_name

    result = f"""
{'='*75}
VENTAS DE {employee_found.upper()} - {date_str}
{'='*75}

Total de órdenes: {len(pos_orders)}
Total vendido: ${total:,.2f}
Promedio por orden: ${total/len(pos_orders):,.2f}

{'='*75}

Detalle de órdenes:
{'-'*75}
"""

    for order in pos_orders:
        partner_name = order['partner_id'][1] if order['partner_id'] else 'CONSUMIDOR FINAL'
        pos_name = order['config_id'][1] if order['config_id'] else 'N/A'
        result += f"{order['name']:15} | {pos_name:15} | {partner_name:25} | ${order['amount_total']:>10,.2f}\n"

    return result


async def get_hourly_sales(date_str: str, pos_config: str | None = None) -> str:
    """Get sales grouped by hour of the day"""

    client = get_odoo_client()

    if date_str.lower() == 'today':
        target_date = date.today()
    else:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    date_start = datetime.combine(target_date, datetime.min.time())
    date_end = datetime.combine(target_date, datetime.max.time())

    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(date_start)),
        ('date_order', '<=', client.datetime_to_odoo_format(date_end)),
        ('state', 'in', ['paid', 'done', 'invoiced'])
    ]

    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))

    pos_orders = client.search_read(
        'pos.order',
        domain,
        ['date_order', 'amount_total']
    )

    if not pos_orders:
        return f"No se encontraron ventas para {date_str}"

    # Group by hour
    hourly = {}
    for order in pos_orders:
        # Parse the datetime and convert to Bogotá timezone
        order_dt = datetime.strptime(utc_to_bogota(order['date_order']), '%Y-%m-%d %H:%M:%S')
        hour = order_dt.hour

        if hour not in hourly:
            hourly[hour] = {'count': 0, 'total': 0}

        hourly[hour]['count'] += 1
        hourly[hour]['total'] += order['amount_total']

    total_all = sum(h['total'] for h in hourly.values())

    result = f"""
{'='*70}
VENTAS POR HORA - {date_str}
{'='*70}

{'Hora':<10} | {'Órdenes':>10} | {'Total':>15} | {'%':>6} | Gráfico
{'-'*70}
"""

    max_total = max(h['total'] for h in hourly.values()) if hourly else 1

    for hour in sorted(hourly.keys()):
        data = hourly[hour]
        pct = (data['total'] / total_all * 100) if total_all > 0 else 0
        bar_len = int((data['total'] / max_total) * 20)
        bar = '█' * bar_len
        result += f"{hour:02d}:00-{hour:02d}:59 | {data['count']:>10} | ${data['total']:>14,.2f} | {pct:>5.1f}% | {bar}\n"

    result += f"""
{'-'*70}
TOTAL: {sum(h['count'] for h in hourly.values())} órdenes | ${total_all:,.2f}
{'='*70}

🔥 Hora pico: {max(hourly.keys(), key=lambda h: hourly[h]['total']):02d}:00 con ${max(h['total'] for h in hourly.values()):,.2f}
"""

    return result


async def get_canceled_orders(date_str: str, pos_config: str | None = None) -> str:
    """Get canceled/returned orders"""

    client = get_odoo_client()

    if date_str.lower() == 'today':
        target_date = date.today()
    else:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    date_start = datetime.combine(target_date, datetime.min.time())
    date_end = datetime.combine(target_date, datetime.max.time())

    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(date_start)),
        ('date_order', '<=', client.datetime_to_odoo_format(date_end)),
        ('state', 'in', ['cancel'])
    ]

    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))

    canceled_orders = client.search_read(
        'pos.order',
        domain,
        ['name', 'date_order', 'amount_total', 'employee_id', 'config_id']
    )

    if not canceled_orders:
        return f"✅ No hay órdenes canceladas para {date_str}"

    total = sum(order['amount_total'] for order in canceled_orders)

    result = f"""
{'='*75}
⚠️ ÓRDENES CANCELADAS - {date_str}
{'='*75}

Total de órdenes canceladas: {len(canceled_orders)}
Monto total cancelado: ${total:,.2f}

{'='*75}

Detalle:
{'-'*75}
{'Orden':<20} | {'Cajero':<20} | {'POS':<15} | {'Monto':>12}
{'-'*75}
"""

    for order in canceled_orders:
        employee = order['employee_id'][1] if order['employee_id'] else 'N/A'
        pos_name = order['config_id'][1] if order['config_id'] else 'N/A'
        result += f"{order['name']:<20} | {employee:<20} | {pos_name:<15} | ${order['amount_total']:>11,.2f}\n"

    return result


async def get_discounts_applied(date_str: str, pos_config: str | None = None) -> str:
    """Get discounts applied by cashier/product"""

    client = get_odoo_client()

    if date_str.lower() == 'today':
        target_date = date.today()
    else:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    date_start = datetime.combine(target_date, datetime.min.time())
    date_end = datetime.combine(target_date, datetime.max.time())

    domain = [
        ('order_id.date_order', '>=', client.datetime_to_odoo_format(date_start)),
        ('order_id.date_order', '<=', client.datetime_to_odoo_format(date_end)),
        ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
        ('discount', '>', 0)
    ]

    if pos_config:
        domain.append(('order_id.config_id.name', 'ilike', pos_config))

    order_lines = client.search_read(
        'pos.order.line',
        domain,
        ['product_id', 'qty', 'price_unit', 'discount', 'price_subtotal_incl', 'order_id']
    )

    if not order_lines:
        return f"✅ No se aplicaron descuentos en {date_str}"

    # Group by employee
    by_employee = {}
    total_discount = 0

    for line in order_lines:
        # Calculate discount amount
        original_price = line['price_unit'] * line['qty']
        discount_amount = original_price * (line['discount'] / 100)
        total_discount += discount_amount

        product_name = line['product_id'][1]

        # Get employee from order
        order_id = line['order_id'][0]

        if order_id not in by_employee:
            by_employee[order_id] = {
                'order_name': line['order_id'][1],
                'lines': [],
                'total_discount': 0
            }

        by_employee[order_id]['lines'].append({
            'product': product_name,
            'discount_pct': line['discount'],
            'discount_amount': discount_amount
        })
        by_employee[order_id]['total_discount'] += discount_amount

    result = f"""
{'='*80}
💰 DESCUENTOS APLICADOS - {date_str}
{'='*80}

Total de líneas con descuento: {len(order_lines)}
Monto total de descuentos: ${total_discount:,.2f}

{'='*80}

Detalle por orden:
{'-'*80}
"""

    for order_id, data in sorted(by_employee.items(), key=lambda x: x[1]['total_discount'], reverse=True):
        result += f"\n📋 {data['order_name']} (Descuentos: ${data['total_discount']:,.2f})\n"
        for line in data['lines'][:5]:  # Top 5 lines per order
            result += f"   • {line['product'][:40]}: {line['discount_pct']}% = -${line['discount_amount']:,.2f}\n"

    return result


# ============================================================================
# NEW ADVANCED ANALYTICS TOOLS
# ============================================================================

async def get_orders_by_time_range(date_str: str, hour_start: int, hour_end: int, pos_config: str | None = None) -> str:
    """Get orders within a specific time range"""

    client = get_odoo_client()

    if date_str.lower() == 'today':
        target_date = date.today()
    else:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Create time range
    time_start = datetime.combine(target_date, datetime.min.time().replace(hour=int(hour_start)))
    time_end = datetime.combine(target_date, datetime.min.time().replace(hour=int(hour_end), minute=59, second=59))

    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(time_start)),
        ('date_order', '<=', client.datetime_to_odoo_format(time_end)),
        ('state', 'in', ['paid', 'done', 'invoiced'])
    ]

    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))

    orders = client.search_read(
        'pos.order',
        domain,
        ['name', 'date_order', 'amount_total', 'partner_id', 'employee_id', 'config_id']
    )

    if not orders:
        return f"No se encontraron órdenes entre {hour_start}:00 y {hour_end}:59 para {date_str}"

    total = sum(o['amount_total'] for o in orders)

    result = f"""
{'='*80}
🕐 ÓRDENES EN RANGO HORARIO {hour_start:02d}:00 - {hour_end:02d}:59 | {date_str}
{'='*80}

Total de órdenes: {len(orders)}
Total vendido: ${total:,.2f}
Promedio por orden: ${total/len(orders):,.2f}

{'='*80}

{'Hora':<8} | {'Orden':<20} | {'Cajero':<20} | {'POS':<15} | {'Monto':>12}
{'-'*80}
"""

    for order in sorted(orders, key=lambda x: x['date_order']):
        order_dt = datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S')
        hour_str = order_dt.strftime('%H:%M')
        employee = order['employee_id'][1][:18] if order['employee_id'] else 'N/A'
        pos_name = order['config_id'][1][:13] if order['config_id'] else 'N/A'
        result += f"{hour_str:<8} | {order['name']:<20} | {employee:<20} | {pos_name:<15} | ${order['amount_total']:>11,.2f}\n"

    return result


async def compare_periods(period1_start: str, period1_end: str, period2_start: str, period2_end: str, pos_config: str | None = None) -> str:
    """Compare sales between two periods"""

    client = get_odoo_client()

    async def get_period_data(start_str, end_str):
        dt_start = datetime.strptime(start_str, "%Y-%m-%d")
        dt_end = datetime.strptime(end_str, "%Y-%m-%d")
        dt_end = datetime.combine(dt_end.date(), datetime.max.time())

        domain = [
            ('date_order', '>=', client.datetime_to_odoo_format(dt_start)),
            ('date_order', '<=', client.datetime_to_odoo_format(dt_end)),
            ('state', 'in', ['paid', 'done', 'invoiced'])
        ]

        if pos_config:
            domain.append(('config_id.name', 'ilike', pos_config))

        orders = client.search_read('pos.order', domain, ['amount_total'])
        total = sum(o['amount_total'] for o in orders)
        count = len(orders)
        return {'total': total, 'count': count, 'avg': total/count if count > 0 else 0}

    p1 = await get_period_data(period1_start, period1_end)
    p2 = await get_period_data(period2_start, period2_end)

    # Calculate differences
    total_diff = p1['total'] - p2['total']
    total_pct = ((p1['total'] - p2['total']) / p2['total'] * 100) if p2['total'] > 0 else 0
    count_diff = p1['count'] - p2['count']
    count_pct = ((p1['count'] - p2['count']) / p2['count'] * 100) if p2['count'] > 0 else 0

    trend_total = "📈" if total_diff > 0 else "📉" if total_diff < 0 else "➡️"
    trend_count = "📈" if count_diff > 0 else "📉" if count_diff < 0 else "➡️"

    result = f"""
{'='*80}
📊 COMPARACIÓN DE PERÍODOS
{'='*80}

                  | PERÍODO 1              | PERÍODO 2              | DIFERENCIA
                  | {period1_start} a {period1_end} | {period2_start} a {period2_end} |
{'-'*80}
Total Ventas      | ${p1['total']:>18,.2f} | ${p2['total']:>18,.2f} | {trend_total} ${total_diff:>+15,.2f} ({total_pct:>+.1f}%)
Órdenes           | {p1['count']:>19} | {p2['count']:>19} | {trend_count} {count_diff:>+16} ({count_pct:>+.1f}%)
Ticket Promedio   | ${p1['avg']:>18,.2f} | ${p2['avg']:>18,.2f} |
{'='*80}
"""

    return result


async def get_product_categories_sales(date_from: str, date_to: str, pos_config: str | None = None) -> str:
    """Get sales grouped by product category"""

    client = get_odoo_client()

    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())

    domain = [
        ('order_id.date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('order_id.date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('order_id.state', 'in', ['paid', 'done', 'invoiced'])
    ]

    if pos_config:
        domain.append(('order_id.config_id.name', 'ilike', pos_config))

    order_lines = client.search_read(
        'pos.order.line',
        domain,
        ['product_id', 'qty', 'price_subtotal_incl']
    )

    if not order_lines:
        return f"No se encontraron ventas entre {date_from} y {date_to}"

    # Get product categories
    product_ids = list(set([line['product_id'][0] for line in order_lines]))
    products = client.search_read(
        'product.product',
        [('id', 'in', product_ids)],
        ['id', 'categ_id']
    )

    product_categ = {p['id']: p['categ_id'][1] if p['categ_id'] else 'Sin Categoría' for p in products}

    # Group by category
    categories = {}
    for line in order_lines:
        cat = product_categ.get(line['product_id'][0], 'Sin Categoría')
        if cat not in categories:
            categories[cat] = {'qty': 0, 'total': 0}
        categories[cat]['qty'] += line['qty']
        categories[cat]['total'] += line['price_subtotal_incl']

    total_all = sum(c['total'] for c in categories.values())
    sorted_cats = sorted(categories.items(), key=lambda x: x[1]['total'], reverse=True)

    result = f"""
{'='*80}
📦 VENTAS POR CATEGORÍA - {date_from} al {date_to}
{'='*80}

{'Categoría':<40} | {'Cantidad':>10} | {'Total':>15} | {'%':>6}
{'-'*80}
"""

    for cat_name, data in sorted_cats:
        pct = (data['total'] / total_all * 100) if total_all > 0 else 0
        result += f"{cat_name[:40]:<40} | {data['qty']:>10.0f} | ${data['total']:>14,.2f} | {pct:>5.1f}%\n"

    result += f"""
{'-'*80}
{'TOTAL':<40} | {sum(c['qty'] for _, c in sorted_cats):>10.0f} | ${total_all:>14,.2f} | 100.0%
{'='*80}
"""

    return result


async def get_sales_by_partner(partner_name: str, date_from: str | None = None, date_to: str | None = None, pos_config: str | None = None) -> str:
    """Get sales for a specific partner/company"""

    client = get_odoo_client()

    domain = [
        ('state', 'in', ['paid', 'done', 'invoiced']),
        ('partner_id.name', 'ilike', partner_name)
    ]

    if date_from:
        dt_from = datetime.strptime(date_from, "%Y-%m-%d")
        domain.append(('date_order', '>=', client.datetime_to_odoo_format(dt_from)))

    if date_to:
        dt_to = datetime.strptime(date_to, "%Y-%m-%d")
        dt_to = datetime.combine(dt_to.date(), datetime.max.time())
        domain.append(('date_order', '<=', client.datetime_to_odoo_format(dt_to)))

    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))

    orders = client.search_read(
        'pos.order',
        domain,
        ['name', 'date_order', 'amount_total', 'partner_id', 'config_id'],
        order='date_order desc',
        limit=100
    )

    if not orders:
        return f"No se encontraron ventas para el cliente '{partner_name}'"

    total = sum(o['amount_total'] for o in orders)
    partner_found = orders[0]['partner_id'][1] if orders[0]['partner_id'] else partner_name

    period_str = ""
    if date_from and date_to:
        period_str = f" ({date_from} al {date_to})"
    elif date_from:
        period_str = f" (desde {date_from})"
    elif date_to:
        period_str = f" (hasta {date_to})"

    result = f"""
{'='*80}
🏢 VENTAS DE {partner_found.upper()}{period_str}
{'='*80}

Total de órdenes: {len(orders)}
Total vendido: ${total:,.2f}
Promedio por orden: ${total/len(orders):,.2f}

{'='*80}

{'Fecha':<12} | {'Orden':<20} | {'POS':<20} | {'Monto':>15}
{'-'*80}
"""

    for order in orders[:50]:  # Limit display to 50
        order_dt = datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S')
        date_str = order_dt.strftime('%Y-%m-%d')
        pos_name = order['config_id'][1][:18] if order['config_id'] else 'N/A'
        result += f"{date_str:<12} | {order['name']:<20} | {pos_name:<20} | ${order['amount_total']:>14,.2f}\n"

    if len(orders) > 50:
        result += f"\n... y {len(orders) - 50} órdenes más"

    return result


async def get_partner_order_history(partner_name: str, limit: int = 50) -> str:
    """Get complete order history for a partner"""

    client = get_odoo_client()

    # First find the partner
    partners = client.search_read(
        'res.partner',
        [('name', 'ilike', partner_name)],
        ['id', 'name', 'email', 'phone', 'street', 'city']
    )

    if not partners:
        return f"No se encontró ningún cliente con nombre '{partner_name}'"

    partner = partners[0]

    # Get all orders for this partner
    orders = client.search_read(
        'pos.order',
        [
            ('partner_id', '=', partner['id']),
            ('state', 'in', ['paid', 'done', 'invoiced'])
        ],
        ['name', 'date_order', 'amount_total', 'config_id', 'lines'],
        order='date_order desc',
        limit=limit
    )

    total_all = sum(o['amount_total'] for o in orders)
    avg_ticket = total_all / len(orders) if orders else 0

    # Get first and last order dates
    first_order = orders[-1]['date_order'] if orders else 'N/A'
    last_order = orders[0]['date_order'] if orders else 'N/A'

    result = f"""
{'='*80}
👤 HISTORIAL DE CLIENTE: {partner['name']}
{'='*80}

📧 Email: {partner.get('email') or 'N/A'}
📱 Teléfono: {partner.get('phone') or 'N/A'}
📍 Dirección: {partner.get('street') or ''} {partner.get('city') or ''}

{'-'*80}
📊 ESTADÍSTICAS
{'-'*80}

Total de órdenes: {len(orders)}
Gasto total: ${total_all:,.2f}
Ticket promedio: ${avg_ticket:,.2f}
Primera compra: {first_order[:10] if first_order != 'N/A' else 'N/A'}
Última compra: {last_order[:10] if last_order != 'N/A' else 'N/A'}

{'-'*80}
📋 ÚLTIMAS ÓRDENES (máx {limit})
{'-'*80}

{'Fecha':<12} | {'Orden':<20} | {'POS':<20} | {'Monto':>15}
{'-'*80}
"""

    for order in orders[:limit]:
        order_dt = datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S')
        date_str = order_dt.strftime('%Y-%m-%d')
        pos_name = order['config_id'][1][:18] if order['config_id'] else 'N/A'
        result += f"{date_str:<12} | {order['name']:<20} | {pos_name:<20} | ${order['amount_total']:>14,.2f}\n"

    result += f"\n{'='*80}\n"

    return result


# ============================================================================
# PRODUCT MANAGEMENT TOOLS
# ============================================================================

async def get_product_details(product_name: str) -> str:
    """Get complete product information"""

    client = get_odoo_client()

    # Search for the product
    products = client.search_read(
        'product.product',
        [('name', 'ilike', product_name)],
        ['id', 'name', 'default_code', 'list_price', 'standard_price', 'categ_id',
         'type', 'available_in_pos', 'active', 'qty_available', 'barcode',
         'description_sale', 'pos_categ_ids'],
        limit=5
    )

    if not products:
        return f"No se encontró ningún producto con nombre '{product_name}'"

    result = f"""
{'='*80}
📦 DETALLES DE PRODUCTO(S)
{'='*80}
"""

    for product in products:
        category = product['categ_id'][1] if product['categ_id'] else 'Sin categoría'
        pos_categs = ', '.join([c[1] for c in product.get('pos_categ_ids', [])]) if product.get('pos_categ_ids') else 'N/A'
        margin = ((product['list_price'] - product['standard_price']) / product['list_price'] * 100) if product['list_price'] > 0 else 0

        result += f"""
{'-'*80}
📌 {product['name']}
{'-'*80}

🔑 ID: {product['id']}
📝 Código interno: {product.get('default_code') or 'N/A'}
🏷️ Código de barras: {product.get('barcode') or 'N/A'}

💰 PRECIOS:
   • Precio de venta: ${product['list_price']:,.2f}
   • Costo: ${product['standard_price']:,.2f}
   • Margen: {margin:.1f}%

📦 INVENTARIO:
   • Stock disponible: {product.get('qty_available', 0):.0f} unidades
   • Tipo: {product['type']}

🏪 CATEGORÍAS:
   • Categoría general: {category}
   • Categorías POS: {pos_categs}

📋 Estado: {'✅ Activo' if product['active'] else '❌ Inactivo'} | {'🏪 Disponible en POS' if product['available_in_pos'] else '📍 No disponible en POS'}

"""

        if product.get('description_sale'):
            result += f"📝 Descripción: {product['description_sale'][:200]}\n"

    return result


async def search_products(query: str, category: str | None = None, limit: int = 20) -> str:
    """Search products by name, code or category"""

    client = get_odoo_client()

    # Build domain
    domain = ['|', '|',
        ('name', 'ilike', query),
        ('default_code', 'ilike', query),
        ('barcode', 'ilike', query)
    ]

    if category:
        domain.append(('categ_id.name', 'ilike', category))

    products = client.search_read(
        'product.product',
        domain,
        ['name', 'default_code', 'list_price', 'categ_id', 'qty_available', 'active', 'available_in_pos'],
        limit=limit
    )

    if not products:
        return f"No se encontraron productos para '{query}'"

    result = f"""
{'='*80}
🔍 RESULTADOS DE BÚSQUEDA: "{query}"
{'='*80}

Encontrados: {len(products)} producto(s)

{'Nombre':<35} | {'Código':<12} | {'Categoría':<20} | {'Precio':>12}
{'-'*80}
"""

    for product in products:
        code = product.get('default_code') or '-'
        category_name = product['categ_id'][1][:18] if product['categ_id'] else 'N/A'
        status = '✅' if product['active'] and product['available_in_pos'] else '⚠️'
        result += f"{status} {product['name'][:33]:<33} | {code:<12} | {category_name:<20} | ${product['list_price']:>11,.2f}\n"

    return result


async def get_product_categories(parent_category: str | None = None) -> str:
    """List all product categories/sections"""

    client = get_odoo_client()

    domain = []
    if parent_category:
        domain.append(('parent_id.name', 'ilike', parent_category))

    categories = client.search_read(
        'product.category',
        domain,
        ['name', 'parent_id', 'complete_name', 'product_count'],
        order='complete_name'
    )

    if not categories:
        return "No se encontraron categorías de productos"

    # Group by parent
    tree = {}
    for cat in categories:
        parent_name = cat['parent_id'][1] if cat['parent_id'] else 'Raíz'
        if parent_name not in tree:
            tree[parent_name] = []
        tree[parent_name].append(cat)

    result = f"""
{'='*80}
CATEGORÍAS DE PRODUCTOS
{'='*80}

Total de categorías: {len(categories)}

"""

    for parent, children in sorted(tree.items()):
        result += f"\n📁 {parent}\n"
        result += f"{'-'*40}\n"
        for cat in children:
            product_count = cat.get('product_count', 0)
            result += f"   └─ {cat['name']:<30} ({product_count} productos)\n"

    result += f"\n{'='*80}\n"

    return result


async def get_products_by_category(category: str, include_subcategories: bool = True, only_available: bool = True, limit: int = 50) -> str:
    """List all products in a specific category/section"""

    client = get_odoo_client()

    # First find the category
    categories = client.search_read(
        'product.category',
        [('name', 'ilike', category)],
        ['id', 'name', 'complete_name']
    )

    if not categories:
        return f"No se encontró la categoría '{category}'"

    # Get category IDs (include subcategories if requested)
    category_ids = [c['id'] for c in categories]
    category_names = [c['name'] for c in categories]

    if include_subcategories:
        # Find all subcategories
        subcats = client.search_read(
            'product.category',
            [('parent_id', 'in', category_ids)],
            ['id', 'name']
        )
        for subcat in subcats:
            if subcat['id'] not in category_ids:
                category_ids.append(subcat['id'])

    # Build domain for products
    domain = [('categ_id', 'in', category_ids)]

    if only_available:
        domain.append(('available_in_pos', '=', True))
        domain.append(('active', '=', True))

    products = client.search_read(
        'product.product',
        domain,
        ['name', 'default_code', 'list_price', 'categ_id', 'qty_available', 'active', 'available_in_pos'],
        limit=limit,
        order='categ_id, name'
    )

    if not products:
        return f"No se encontraron productos en la categoría '{category}'"

    # Group products by category
    by_category = {}
    for product in products:
        cat_name = product['categ_id'][1] if product['categ_id'] else 'Sin categoría'
        if cat_name not in by_category:
            by_category[cat_name] = []
        by_category[cat_name].append(product)

    result = f"""
{'='*95}
PRODUCTOS EN CATEGORÍA: {', '.join(category_names).upper()}
{'='*95}

Total de productos: {len(products)}
{'Incluye subcategorías' if include_subcategories else 'Solo categoría principal'}

"""

    for cat_name, prods in sorted(by_category.items()):
        result += f"\n📁 {cat_name} ({len(prods)} productos)\n"
        result += f"{'-'*95}\n"
        result += f"{'#':<4} | {'Producto':<40} | {'Código':<12} | {'Stock':>8} | {'Precio':>12}\n"
        result += f"{'-'*95}\n"

        for i, prod in enumerate(prods, 1):
            code = prod.get('default_code') or '-'
            stock = prod.get('qty_available', 0)
            status = '✅' if prod['active'] and prod['available_in_pos'] else '⚠️'
            result += f"{status}{i:<3} | {prod['name'][:38]:<40} | {code:<12} | {stock:>8.1f} | ${prod['list_price']:>11,.2f}\n"

    result += f"\n{'='*95}\n"

    return result


async def update_product_price(product_name: str, new_price: float) -> str:
    """Update product sale price (WRITE operation)"""

    client = get_odoo_client()

    # First find the exact product
    products = client.search_read(
        'product.product',
        [('name', '=', product_name)],
        ['id', 'name', 'list_price', 'default_code']
    )

    if not products:
        # Try with ilike if exact match fails
        products = client.search_read(
            'product.product',
            [('name', 'ilike', product_name)],
            ['id', 'name', 'list_price', 'default_code'],
            limit=5
        )

        if not products:
            return f"❌ No se encontró ningún producto con nombre '{product_name}'"

        if len(products) > 1:
            result = f"⚠️ Se encontraron múltiples productos. Por favor especifica el nombre exacto:\n\n"
            for p in products:
                result += f"• {p['name']} (código: {p.get('default_code') or 'N/A'}) - Precio actual: ${p['list_price']:,.2f}\n"
            return result

    product = products[0]
    old_price = product['list_price']

    # Update the price using write
    try:
        client.models.execute_kw(
            client.db, client.uid, client.password,
            'product.product', 'write',
            [[product['id']], {'list_price': new_price}]
        )

        result = f"""
{'='*80}
✅ PRECIO ACTUALIZADO EXITOSAMENTE
{'='*80}

📦 Producto: {product['name']}
🔑 ID: {product['id']}
📝 Código: {product.get('default_code') or 'N/A'}

💰 CAMBIO DE PRECIO:
   • Precio anterior: ${old_price:,.2f}
   • Precio nuevo: ${new_price:,.2f}
   • Diferencia: ${new_price - old_price:+,.2f} ({((new_price - old_price) / old_price * 100) if old_price > 0 else 0:+.1f}%)

{'='*80}
"""
        return result

    except Exception as e:
        return f"❌ Error al actualizar el precio: {str(e)}"


# ============================================================================
# EMPLOYEE PERFORMANCE TOOLS
# ============================================================================

async def get_employee_performance(employee_name: str, date_from: str, date_to: str, pos_config: str | None = None) -> str:
    """Get performance metrics for a specific employee"""

    client = get_odoo_client()

    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())

    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('state', 'in', ['paid', 'done', 'invoiced']),
        ('employee_id.name', 'ilike', employee_name)
    ]

    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))

    orders = client.search_read(
        'pos.order',
        domain,
        ['name', 'date_order', 'amount_total', 'config_id', 'employee_id', 'lines']
    )

    if not orders:
        return f"No se encontraron órdenes para el empleado '{employee_name}' en el período especificado"

    employee_found = orders[0]['employee_id'][1] if orders[0]['employee_id'] else employee_name

    total_sales = sum(o['amount_total'] for o in orders)
    order_count = len(orders)
    avg_ticket = total_sales / order_count if order_count > 0 else 0

    # Get product count from order lines
    total_products = sum(len(o.get('lines', [])) for o in orders)

    # Group by day
    daily_sales = {}
    for order in orders:
        order_dt = datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S')
        day = order_dt.strftime('%Y-%m-%d')
        if day not in daily_sales:
            daily_sales[day] = {'orders': 0, 'total': 0}
        daily_sales[day]['orders'] += 1
        daily_sales[day]['total'] += order['amount_total']

    days_worked = len(daily_sales)
    avg_daily_sales = total_sales / days_worked if days_worked > 0 else 0
    avg_daily_orders = order_count / days_worked if days_worked > 0 else 0

    # Find best and worst day
    best_day = max(daily_sales.items(), key=lambda x: x[1]['total']) if daily_sales else None
    worst_day = min(daily_sales.items(), key=lambda x: x[1]['total']) if daily_sales else None

    result = f"""
{'='*80}
👤 RENDIMIENTO DE {employee_found.upper()}
{'='*80}

📅 Período: {date_from} al {date_to}
{'Filtro POS: ' + pos_config if pos_config else ''}

{'-'*80}
📊 MÉTRICAS PRINCIPALES
{'-'*80}

Total de ventas: ${total_sales:,.2f}
Total de órdenes: {order_count}
Ticket promedio: ${avg_ticket:,.2f}
Productos vendidos: ~{total_products}

{'-'*80}
📈 PROMEDIOS DIARIOS
{'-'*80}

Días trabajados: {days_worked}
Ventas diarias promedio: ${avg_daily_sales:,.2f}
Órdenes diarias promedio: {avg_daily_orders:.1f}

{'-'*80}
🏆 DÍAS DESTACADOS
{'-'*80}
"""

    if best_day:
        result += f"🥇 Mejor día: {best_day[0]} - ${best_day[1]['total']:,.2f} ({best_day[1]['orders']} órdenes)\n"
    if worst_day:
        result += f"📉 Día más bajo: {worst_day[0]} - ${worst_day[1]['total']:,.2f} ({worst_day[1]['orders']} órdenes)\n"

    result += f"""
{'-'*80}
📋 DETALLE DIARIO
{'-'*80}

{'Fecha':<12} | {'Órdenes':>10} | {'Ventas':>15} | {'Ticket Prom':>12}
{'-'*80}
"""

    for day, data in sorted(daily_sales.items()):
        avg = data['total'] / data['orders'] if data['orders'] > 0 else 0
        result += f"{day:<12} | {data['orders']:>10} | ${data['total']:>14,.2f} | ${avg:>11,.2f}\n"

    result += f"\n{'='*80}\n"

    return result


async def get_best_employee_by_metric(metric: str, date_from: str, date_to: str, pos_config: str | None = None, limit: int = 10) -> str:
    """Get best employees by a specific metric"""

    client = get_odoo_client()

    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())

    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('state', 'in', ['paid', 'done', 'invoiced']),
        ('employee_id', '!=', False)
    ]

    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))

    orders = client.search_read(
        'pos.order',
        domain,
        ['amount_total', 'employee_id', 'lines']
    )

    if not orders:
        return f"No se encontraron órdenes en el período especificado"

    # Group by employee
    employees = {}
    for order in orders:
        emp_id = order['employee_id'][0]
        emp_name = order['employee_id'][1]

        if emp_id not in employees:
            employees[emp_id] = {
                'name': emp_name,
                'orders': 0,
                'total': 0,
                'products': 0
            }

        employees[emp_id]['orders'] += 1
        employees[emp_id]['total'] += order['amount_total']
        employees[emp_id]['products'] += len(order.get('lines', []))

    # Calculate averages
    for emp in employees.values():
        emp['avg_ticket'] = emp['total'] / emp['orders'] if emp['orders'] > 0 else 0

    # Sort by metric
    metric_lower = metric.lower()
    if metric_lower in ['ventas', 'sales', 'total']:
        sorted_emps = sorted(employees.values(), key=lambda x: x['total'], reverse=True)
        metric_label = "Ventas Totales"
        value_format = lambda x: f"${x['total']:,.2f}"
    elif metric_lower in ['ordenes', 'orders']:
        sorted_emps = sorted(employees.values(), key=lambda x: x['orders'], reverse=True)
        metric_label = "Órdenes"
        value_format = lambda x: f"{x['orders']}"
    elif metric_lower in ['ticket_promedio', 'ticket', 'avg']:
        sorted_emps = sorted(employees.values(), key=lambda x: x['avg_ticket'], reverse=True)
        metric_label = "Ticket Promedio"
        value_format = lambda x: f"${x['avg_ticket']:,.2f}"
    elif metric_lower in ['productos', 'products']:
        sorted_emps = sorted(employees.values(), key=lambda x: x['products'], reverse=True)
        metric_label = "Productos Vendidos"
        value_format = lambda x: f"{x['products']}"
    else:
        return f"❌ Métrica no válida: {metric}. Usa: 'ventas', 'ordenes', 'ticket_promedio', 'productos'"

    sorted_emps = sorted_emps[:limit]

    result = f"""
{'='*80}
🏆 RANKING DE EMPLEADOS POR {metric_label.upper()}
{'='*80}

📅 Período: {date_from} al {date_to}
{'Filtro POS: ' + pos_config if pos_config else ''}

{'Pos':<5} | {'Empleado':<30} | {'Órdenes':>10} | {'Ventas':>15} | {'Ticket Prom':>12}
{'-'*80}
"""

    medals = ['🥇', '🥈', '🥉']
    for i, emp in enumerate(sorted_emps):
        pos_str = medals[i] if i < 3 else f"{i+1}."
        result += f"{pos_str:<5} | {emp['name'][:28]:<30} | {emp['orders']:>10} | ${emp['total']:>14,.2f} | ${emp['avg_ticket']:>11,.2f}\n"

    # Summary
    total_all = sum(e['total'] for e in sorted_emps)
    orders_all = sum(e['orders'] for e in sorted_emps)

    result += f"""
{'-'*80}
📊 RESUMEN TOP {limit}
{'-'*80}

Total empleados: {len(sorted_emps)}
Ventas totales: ${total_all:,.2f}
Órdenes totales: {orders_all}

{'='*80}
"""

    return result


async def get_employee_products_sold(employee_name: str, date_from: str, date_to: str, pos_config: str | None = None, limit: int = 30) -> str:
    """Get products sold by a specific employee with quantities and amounts"""

    client = get_odoo_client()

    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())

    # Build domain for pos.order
    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('state', 'in', ['paid', 'done', 'invoiced']),
        ('employee_id.name', 'ilike', employee_name)
    ]

    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))

    # Get orders for this employee
    orders = client.search_read(
        'pos.order',
        domain,
        ['id', 'name', 'date_order', 'amount_total', 'employee_id', 'config_id', 'lines']
    )

    if not orders:
        return f"No se encontraron ventas para el empleado '{employee_name}' en el período {date_from} al {date_to}"

    employee_found = orders[0]['employee_id'][1] if orders[0]['employee_id'] else employee_name

    # Get all order line IDs
    all_line_ids = []
    for order in orders:
        all_line_ids.extend(order.get('lines', []))

    if not all_line_ids:
        return f"No se encontraron líneas de productos para el empleado '{employee_name}'"

    # Get order lines with product details
    lines = client.search_read(
        'pos.order.line',
        [('id', 'in', all_line_ids)],
        ['product_id', 'qty', 'price_unit', 'discount', 'price_subtotal_incl', 'order_id']
    )

    # Aggregate products
    products = {}
    for line in lines:
        if not line['product_id']:
            continue

        product_id = line['product_id'][0]
        product_name = line['product_id'][1]

        if product_id not in products:
            products[product_id] = {
                'name': product_name,
                'qty': 0,
                'total': 0,
                'orders_count': 0,
                'avg_price': 0
            }

        products[product_id]['qty'] += line['qty']
        products[product_id]['total'] += line['price_subtotal_incl']
        products[product_id]['orders_count'] += 1

    # Calculate average price per product
    for product_id in products:
        if products[product_id]['qty'] > 0:
            products[product_id]['avg_price'] = products[product_id]['total'] / products[product_id]['qty']

    # Sort by total amount (descending) and limit
    sorted_products = sorted(products.values(), key=lambda x: x['total'], reverse=True)[:limit]

    # Calculate totals
    total_qty = sum(p['qty'] for p in sorted_products)
    total_amount = sum(p['total'] for p in sorted_products)
    total_orders = len(orders)

    result = f"""
{'='*95}
PRODUCTOS VENDIDOS POR: {employee_found.upper()}
{'='*95}

Período: {date_from} al {date_to}
{'Punto de venta: ' + pos_config if pos_config else ''}
Total de órdenes: {total_orders}

{'-'*95}
{'#':<4} | {'Producto':<40} | {'Cantidad':>10} | {'Precio Prom':>12} | {'Total':>15}
{'-'*95}
"""

    for i, prod in enumerate(sorted_products, 1):
        result += f"{i:<4} | {prod['name'][:38]:<40} | {prod['qty']:>10.2f} | ${prod['avg_price']:>11,.2f} | ${prod['total']:>14,.2f}\n"

    result += f"""
{'-'*95}
{'TOTALES':<4} | {'':<40} | {total_qty:>10.2f} | {'':<12} | ${total_amount:>14,.2f}
{'='*95}

Resumen:
- Productos diferentes vendidos: {len(sorted_products)}
- Cantidad total de items: {total_qty:.2f}
- Monto total vendido: ${total_amount:,.2f}
- Ticket promedio: ${total_amount/total_orders:,.2f}

{'='*95}
"""

    return result


# ============================================================================
# POS ORDER REPORTS
# ============================================================================

async def get_order_details(order_name: str) -> str:
    """Get complete details for a specific POS order"""
    client = get_odoo_client()
    
    # Search for the order
    orders = client.search_read(
        'pos.order',
        [('name', '=', order_name)],
        ['name', 'date_order', 'amount_total', 'amount_tax', 'amount_paid', 'amount_return',
         'partner_id', 'employee_id', 'config_id', 'session_id', 'state', 'lines', 'payment_ids']
    )
    
    if not orders:
        return f"No se encontró la orden '{order_name}'"
    
    order = orders[0]
    
    # Get lines
    lines = client.search_read(
        'pos.order.line',
        [('id', 'in', order['lines'])],
        ['product_id', 'qty', 'price_unit', 'discount', 'price_subtotal_incl']
    )
    
    # Get payments
    payments = client.search_read(
        'pos.payment',
        [('id', 'in', order['payment_ids'])],
        ['payment_method_id', 'amount', 'payment_date']
    )
    
    result = f"""
{'='*80}
📄 DETALLE DE ORDEN: {order['name']}
{'='*80}

📅 Fecha: {order['date_order']}
👤 Cliente: {order['partner_id'][1] if order['partner_id'] else 'N/A'}
👨‍🍳 Empleado: {order['employee_id'][1] if order['employee_id'] else 'N/A'}
🏪 POS: {order['config_id'][1] if order['config_id'] else 'N/A'}
📊 Estado: {order['state'].upper()}

{'-'*80}
🛒 PRODUCTOS
{'-'*80}
{'Producto':<40} | {'Cant':>6} | {'Precio':>12} | {'Total':>12}
{'-'*80}
"""
    for line in lines:
        result += f"{line['product_id'][1][:40]:<40} | {line['qty']:>6.2f} | ${line['price_unit']:>11,.2f} | ${line['price_subtotal_incl']:>11,.2f}\n"

    result += f"""
{'-'*80}
💰 RESUMEN ECONÓMICO
{'-'*80}
   • Subtotal (inc. impuestos): ${order['amount_total']:,.2f}
   • Impuestos:                 ${order['amount_tax']:,.2f}
   • TOTAL:                     ${order['amount_total']:,.2f}
   • Pagado:                    ${order['amount_paid']:,.2f}
   • Cambio:                    ${order['amount_return']:,.2f}

{'-'*80}
💳 PAGOS
{'-'*80}
"""
    for pay in payments:
        result += f"   • {pay['payment_method_id'][1]:<20} | ${pay['amount']:>12,.2f} | {pay['payment_date']}\n"

    result += f"\n{'='*80}\n"
    return result


async def search_orders(query: str, min_amount: float = None, max_amount: float = None, limit: int = 20) -> str:
    """Search for POS orders by reference or partner name"""
    client = get_odoo_client()
    
    domain = ['|', ('name', 'ilike', query), ('partner_id.name', 'ilike', query)]
    
    if min_amount is not None:
        domain.append(('amount_total', '>=', min_amount))
    if max_amount is not None:
        domain.append(('amount_total', '<=', max_amount))
        
    orders = client.search_read(
        'pos.order',
        domain,
        ['name', 'date_order', 'partner_id', 'amount_total', 'state'],
        order='date_order desc',
        limit=limit
    )
    
    if not orders:
        return f"No se encontraron órdenes para '{query}'"
        
    result = f"""
{'='*80}
🔍 RESULTADOS DE BÚSQUEDA: "{query}"
{'='*80}

{'Referencia':<20} | {'Fecha (Bogotá)':<16} | {'Cliente':<25} | {'Estado':<10} | {'Monto':>12}
{'-'*90}
"""
    for o in orders:
        partner = o['partner_id'][1][:25] if o['partner_id'] else 'N/A'
        date_local = utc_to_bogota(o['date_order'])[:16]  # Convert UTC to Bogotá
        result += f"{o['name']:<20} | {date_local:<16} | {partner:<25} | {o['state']:<10} | ${o['amount_total']:>11,.2f}\n"

    return result


async def get_daily_summary(date_str: str, pos_config: str | None = None) -> str:
    """Generate a daily executive summary"""
    client = get_odoo_client()
    
    if date_str.lower() == 'today':
        target_date = date.today()
    else:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
    date_start = datetime.combine(target_date, datetime.min.time())
    date_end = datetime.combine(target_date, datetime.max.time())
    
    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(date_start)),
        ('date_order', '<=', client.datetime_to_odoo_format(date_end)),
        ('state', 'in', ['paid', 'done', 'invoiced'])
    ]
    
    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))
        
    orders = client.search_read(
        'pos.order',
        domain,
        ['amount_total', 'employee_id', 'payment_ids', 'lines']
    )
    
    if not orders:
        return f"No hay actividad comercial registrada para {date_str}"
        
    total_sales = sum(o['amount_total'] for o in orders)
    order_count = len(orders)
    avg_ticket = total_sales / order_count if order_count > 0 else 0
    
    # Payments summary
    payment_ids = []
    for o in orders:
        payment_ids.extend(o['payment_ids'])
        
    payments = client.search_read(
        'pos.payment',
        [('id', 'in', payment_ids)],
        ['payment_method_id', 'amount']
    )
    
    pm_summary = {}
    for p in payments:
        pm_name = p['payment_method_id'][1]
        pm_summary[pm_name] = pm_summary.get(pm_name, 0) + p['amount']
        
    # Employee summary
    emp_summary = {}
    for o in orders:
        emp_name = o['employee_id'][1] if o['employee_id'] else 'N/A'
        emp_summary[emp_name] = emp_summary.get(emp_name, 0) + o['amount_total']
        
    result = f"""
{'='*80}
🏢 RESUMEN EJECUTIVO DIARIO: {date_str}
{'='*80}
{'Filtro POS: ' + pos_config if pos_config else 'Todos los POS'}

📊 GENERAL
{'-'*80}
Ventas Totales:  ${total_sales:,.2f}
Total Órdenes:   {order_count}
Ticket Promedio: ${avg_ticket:,.2f}

💳 MÉTODOS DE PAGO
{'-'*80}
"""
    for pm, amt in sorted(pm_summary.items(), key=lambda x: x[1], reverse=True):
        result += f"{pm:<30} | ${amt:>15,.2f}\n"
        
    result += f"""
👨‍🍳 VENTAS POR EMPLEADO
{'-'*80}
"""
    for emp, amt in sorted(emp_summary.items(), key=lambda x: x[1], reverse=True):
        result += f"{emp:<30} | ${amt:>15,.2f}\n"

    result += f"\n{'='*80}\n"
    return result


async def get_most_frequent_customers(date_from: str, date_to: str, limit: int = 10) -> str:
    """Identify customers with highest purchase frequency"""
    client = get_odoo_client()
    
    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())
    
    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('state', 'in', ['paid', 'done', 'invoiced']),
        ('partner_id', '!=', False)
    ]
    
    orders = client.search_read('pos.order', domain, ['partner_id', 'amount_total'])
    
    stats = {}
    for o in orders:
        pid = o['partner_id'][1]
        if pid not in stats:
            stats[pid] = {'count': 0, 'total': 0}
        stats[pid]['count'] += 1
        stats[pid]['total'] += o['amount_total']
        
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['count'], reverse=True)[:limit]
    
    result = f"""
{'='*80}
👥 CLIENTES MÁS FRECUENTES ({date_from} al {date_to})
{'='*80}

{'Pos':<4} | {'Cliente':<35} | {'Visitas':>10} | {'Gasto Total':>15} | {'Promedio':>12}
{'-'*80}
"""
    for i, (name, data) in enumerate(sorted_stats):
        avg = data['total'] / data['count']
        result += f"{i+1:<4} | {name[:35]:<35} | {data['count']:>10} | ${data['total']:>14,.2f} | ${avg:>11,.2f}\n"
        
    return result


async def get_sales_by_weekday(date_from: str, date_to: str, pos_config: str | None = None) -> str:
    """Group sales by day of the week"""
    client = get_odoo_client()
    
    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())
    
    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('state', 'in', ['paid', 'done', 'invoiced'])
    ]
    
    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))
        
    orders = client.search_read('pos.order', domain, ['date_order', 'amount_total'])
    
    days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    weekday_stats = {i: {'count': 0, 'total': 0} for i in range(7)}
    
    for o in orders:
        dt = datetime.strptime(o['date_order'], '%Y-%m-%d %H:%M:%S')
        wd = dt.weekday()
        weekday_stats[wd]['count'] += 1
        weekday_stats[wd]['total'] += o['amount_total']
        
    total_total = sum(d['total'] for d in weekday_stats.values())
    
    result = f"""
{'='*80}
📅 VENTAS POR DÍA DE LA SEMANA ({date_from} al {date_to})
{'='*80}

{'Día':<12} | {'Órdenes':>10} | {'Total Vendido':>18} | {'%':>10}
{'-'*80}
"""
    for i in range(7):
        data = weekday_stats[i]
        pct = (data['total'] / total_total * 100) if total_total > 0 else 0
        result += f"{days[i]:<12} | {data['count']:>10} | ${data['total']:>17,.2f} | {pct:>9.1f}%\n"
        
    return result


async def get_peak_hours_analysis(date_from: str, date_to: str, pos_config: str | None = None) -> str:
    """Analyze busiest hours of operation"""
    client = get_odoo_client()
    
    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())
    
    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('state', 'in', ['paid', 'done', 'invoiced'])
    ]
    
    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))
        
    orders = client.search_read('pos.order', domain, ['date_order', 'amount_total'])
    
    hourly_stats = {h: {'count': 0, 'total': 0} for h in range(24)}
    for o in orders:
        dt = datetime.strptime(o['date_order'], '%Y-%m-%d %H:%M:%S')
        h = dt.hour
        hourly_stats[h]['count'] += 1
        hourly_stats[h]['total'] += o['amount_total']
        
    result = f"""
{'='*80}
🔥 ANÁLISIS DE HORAS PICO ({date_from} al {date_to})
{'='*80}

{'Hora':<8} | {'Órdenes':>10} | {'Total':>15} | {'Gráfico'}
{'-'*80}
"""
    max_total = max(h['total'] for h in hourly_stats.values()) if orders else 0
    
    for h in range(24):
        data = hourly_stats[h]
        if data['count'] == 0: continue
        
        bars = int((data['total'] / max_total * 20)) if max_total > 0 else 0
        graph = '█' * bars
        result += f"{h:02d}:00    | {data['count']:>10} | ${data['total']:>14,.2f} | {graph}\n"
        
    return result


async def get_month_over_month(month: int, year: int, pos_config: str | None = None) -> str:
    """Compare monthly performance with previous month"""
    client = get_odoo_client()
    
    # Current month
    dt_start = datetime(year, month, 1)
    if month == 12:
        dt_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        dt_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
    # Previous month
    if month == 1:
        prev_start = datetime(year - 1, 12, 1)
        prev_end = datetime(year, 1, 1) - timedelta(seconds=1)
    else:
        prev_start = datetime(year, month - 1, 1)
        prev_end = datetime(year, month, 1) - timedelta(seconds=1)

    async def get_data(start, end):
        domain = [
            ('date_order', '>=', client.datetime_to_odoo_format(start)),
            ('date_order', '<=', client.datetime_to_odoo_format(end)),
            ('state', 'in', ['paid', 'done', 'invoiced'])
        ]
        if pos_config:
            domain.append(('config_id.name', 'ilike', pos_config))
        orders = client.search_read('pos.order', domain, ['amount_total'])
        return {
            'total': sum(o['amount_total'] for o in orders),
            'count': len(orders)
        }

    current = await get_data(dt_start, dt_end)
    previous = await get_data(prev_start, prev_end)
    
    growth = ((current['total'] - previous['total']) / previous['total'] * 100) if previous['total'] > 0 else 0
    icon = '📈' if growth > 0 else '📉' if growth < 0 else '➡️'
    
    result = f"""
{'='*80}
📅 COMPARATIVA MES A MES
{'='*80}

MÉTRICA        | MES ACTUAL ({month}/{year}) | MES ANTERIOR | CRECIMIENTO
{'-'*80}
Total Ventas   | ${current['total']:>16,.2f} | ${previous['total']:>12,.2f} | {icon} {growth:>+.1f}%
Total Órdenes  | {current['count']:>17} | {previous['count']:>12} | {((current['count']-previous['count'])/previous['count']*100 if previous['count']>0 else 0):>+.1f}%
Ticket Prom.   | ${current['total']/current['count'] if current['count']>0 else 0:>16,.2f} | ${previous['total']/previous['count'] if previous['count']>0 else 0:>12,.2f} |
{'='*80}
"""
    return result


async def get_growth_trends(period: str, limit: int = 4, pos_config: str | None = None) -> str:
    """Analyze growth trends (weekly or monthly)"""
    client = get_odoo_client()
    is_weekly = period.lower() == 'semanal'
    
    now = datetime.now()
    trends = []
    
    for i in range(limit):
        if is_weekly:
            end = now - timedelta(days=now.weekday() + (i * 7))
            start = end - timedelta(days=6)
            label = f"S{start.isocalendar()[1]}"
        else:
            # Monthly
            dt = now.replace(day=1)
            for _ in range(i):
                if dt.month == 1:
                    dt = dt.replace(year=dt.year-1, month=12)
                else:
                    dt = dt.replace(month=dt.month-1)
            start = dt
            if dt.month == 12:
                end = datetime(dt.year+1, 1, 1) - timedelta(seconds=1)
            else:
                end = datetime(dt.year, dt.month+1, 1) - timedelta(seconds=1)
            label = start.strftime('%b %Y')
            
        domain = [
            ('date_order', '>=', client.datetime_to_odoo_format(start)),
            ('date_order', '<=', client.datetime_to_odoo_format(end)),
            ('state', 'in', ['paid', 'done', 'invoiced'])
        ]
        if pos_config:
            domain.append(('config_id.name', 'ilike', pos_config))
            
        orders = client.search_read('pos.order', domain, ['amount_total'])
        total = sum(o['amount_total'] for o in orders)
        trends.append({'label': label, 'total': total})
        
    trends.reverse()
    
    result = f"""
{'='*80}
📈 TENDENCIA DE CRECIMIENTO ({period.upper()})
{'='*80}

{'Período':<15} | {'Ventas':>15} | {'Crecimiento':>15}
{'-'*80}
"""
    for i, t in enumerate(trends):
        growth = ""
        if i > 0 and trends[i-1]['total'] > 0:
            g = (t['total'] - trends[i-1]['total']) / trends[i-1]['total'] * 100
            growth = f"{g:>+14.1f}%"
        result += f"{t['label']:<15} | ${t['total']:>14,.2f} | {growth}\n"
        
    return result


# ============================================================================
# RESTAURANT SPECIFIC TOOLS
# ============================================================================

async def get_restaurant_layout(floor_name: str | None = None) -> str:
    """Get restaurant floor and table layout"""
    client = get_odoo_client()
    
    # Get floors
    domain = []
    if floor_name:
        domain.append(('name', 'ilike', floor_name))
        
    floors = client.search_read(
        'restaurant.floor',
        domain,
        ['name', 'pos_config_id']
    )
    
    if not floors:
        return f"No se encontraron pisos/áreas configuradas"
        
    result = f"""
{'='*80}
🗺️ DISTRIBUCIÓN DEL RESTAURANTE
{'='*80}
"""
    
    for floor in floors:
        floor_id = floor['id']
        floor_name = floor['name']
        pos_config = floor['pos_config_id'][1] if floor['pos_config_id'] else "Todos"
        
        result += f"\n🏢 PISO: {floor_name} (POS: {pos_config})\n"
        result += f"{'-'*80}\n"
        
        # Get tables for this floor
        tables = client.search_read(
            'restaurant.table',
            [('floor_id', '=', floor_id)],
            ['name', 'seats', 'shape']
        )
        
        result += f"{'Mesa':<20} | {'Asientos':>10} | {'Forma':<15}\n"
        result += f"{'-'*80}\n"
        
        for table in tables:
            result += f"{table['name']:<20} | {table['seats']:>10} | {table['shape']:<15}\n"
            
    return result


async def get_guest_metrics(date_from: str, date_to: str, pos_config: str | None = None) -> str:
    """Analyze guest metrics (customer count from POS orders)"""
    client = get_odoo_client()
    
    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())
    
    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('state', 'in', ['paid', 'done', 'invoiced']),
        ('table_id', '!=', False) # Only restaurant orders
    ]
    
    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))
        
    orders = client.search_read(
        'pos.order',
        domain,
        ['amount_total', 'customer_count', 'table_id', 'floor_id']
    )
    
    if not orders:
        return f"No se encontraron órdenes de mesa en el período"
        
    total_sales = sum(o['amount_total'] for o in orders)
    total_orders = len(orders)
    total_guests = sum(o['customer_count'] or 1 for o in orders) # Fallback to 1 if 0/None
    
    avg_guest_spend = total_sales / total_guests if total_guests > 0 else 0
    avg_guests_per_table = total_guests / total_orders if total_orders > 0 else 0
    
    # Group by floor
    floors = {}
    for o in orders:
        fname = o['floor_id'][1] if o['floor_id'] else 'Otros'
        if fname not in floors:
             floors[fname] = {'guests': 0, 'sales': 0, 'orders': 0}
        floors[fname]['guests'] += o['customer_count'] or 1
        floors[fname]['sales'] += o['amount_total']
        floors[fname]['orders'] += 1
        
    result = f"""
{'='*80}
👥 ANÁLISIS DE COMENSALES ({date_from} al {date_to})
{'='*80}

📊 MÉTRICAS GENERALES
{'-'*80}
Total Comensales:    {total_guests}
Total Ventas (Mesas): ${total_sales:,.2f}
Gasto Promedio/Pers: ${avg_guest_spend:,.2f}
Prom. Pers/Mesa:     {avg_guests_per_table:.1f}

🏢 METRICAS POR PISO
{'-'*80}
{'Piso':<20} | {'Personas':>10} | {'Ventas':>15} | {'$/Pers':>12}
{'-'*80}
"""

    for floor, data in sorted(floors.items(), key=lambda x: x[1]['sales'], reverse=True):
        avg = data['sales'] / data['guests'] if data['guests'] > 0 else 0
        result += f"{floor:<20} | {data['guests']:>10} | ${data['sales']:>14,.2f} | ${avg:>11,.2f}\n"

    return result


# ============================================================================
# RESTAURANT SPECIFIC TOOLS
# ============================================================================

async def get_restaurant_layout(floor_name: str | None = None) -> str:
    """Get restaurant floor and table layout"""
    client = get_odoo_client()
    
    # Get floors
    domain = []
    if floor_name:
        domain.append(('name', 'ilike', floor_name))
        
    floors = client.search_read(
        'restaurant.floor',
        domain,
        ['name', 'pos_config_id']
    )
    
    if not floors:
        return f"No se encontraron pisos/áreas configuradas"
        
    result = f"""
{'='*80}
🗺️ DISTRIBUCIÓN DEL RESTAURANTE
{'='*80}
"""
    
    for floor in floors:
        floor_id = floor['id']
        floor_name = floor['name']
        pos_config = floor['pos_config_id'][1] if floor['pos_config_id'] else "Todos"
        
        result += f"\n🏢 PISO: {floor_name} (POS: {pos_config})\n"
        result += f"{'-'*80}\n"
        
        # Get tables for this floor
        tables = client.search_read(
            'restaurant.table',
            [('floor_id', '=', floor_id)],
            ['name', 'seats', 'shape']
        )
        
        result += f"{'Mesa':<20} | {'Asientos':>10} | {'Forma':<15}\n"
        result += f"{'-'*80}\n"
        
        for table in tables:
            result += f"{table['name']:<20} | {table['seats']:>10} | {table['shape']:<15}\n"
            
    return result


async def get_guest_metrics(date_from: str, date_to: str, pos_config: str | None = None) -> str:
    """Analyze guest metrics (customer count from POS orders)"""
    client = get_odoo_client()
    
    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())
    
    domain = [
        ('date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('state', 'in', ['paid', 'done', 'invoiced']),
        ('table_id', '!=', False) # Only restaurant orders
    ]
    
    if pos_config:
        domain.append(('config_id.name', 'ilike', pos_config))
        
    orders = client.search_read(
        'pos.order',
        domain,
        ['amount_total', 'customer_count', 'table_id', 'floor_id']
    )
    
    if not orders:
        return f"No se encontraron órdenes de mesa en el período"
        
    total_sales = sum(o['amount_total'] for o in orders)
    total_orders = len(orders)
    total_guests = sum(o['customer_count'] or 1 for o in orders) # Fallback to 1 if 0/None
    
    avg_guest_spend = total_sales / total_guests if total_guests > 0 else 0
    avg_guests_per_table = total_guests / total_orders if total_orders > 0 else 0
    
    # Group by floor
    floors = {}
    for o in orders:
        fname = o['floor_id'][1] if o['floor_id'] else 'Otros'
        if fname not in floors:
             floors[fname] = {'guests': 0, 'sales': 0, 'orders': 0}
        floors[fname]['guests'] += o['customer_count'] or 1
        floors[fname]['sales'] += o['amount_total']
        floors[fname]['orders'] += 1
        
    result = f"""
{'='*80}
👥 ANÁLISIS DE COMENSALES ({date_from} al {date_to})
{'='*80}

📊 MÉTRICAS GENERALES
{'-'*80}
Total Comensales:    {total_guests}
Total Ventas (Mesas): ${total_sales:,.2f}
Gasto Promedio/Pers: ${avg_guest_spend:,.2f}
Prom. Pers/Mesa:     {avg_guests_per_table:.1f}

🏢 METRICAS POR PISO
{'-'*80}
{'Piso':<20} | {'Personas':>10} | {'Ventas':>15} | {'$/Pers':>12}
{'-'*80}
"""

    for floor, data in sorted(floors.items(), key=lambda x: x[1]['sales'], reverse=True):
        avg = data['sales'] / data['guests'] if data['guests'] > 0 else 0
        result += f"{floor:<20} | {data['guests']:>10} | ${data['sales']:>14,.2f} | ${avg:>11,.2f}\n"

    return result


async def get_kitchen_stats(date_from: str, date_to: str, pos_config: str | None = None) -> str:
    """Analyze kitchen stats: products ordered by hour"""
    client = get_odoo_client()
    
    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())
    
    domain = [
        ('order_id.date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('order_id.date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('order_id.state', 'in', ['paid', 'done', 'invoiced'])
    ]
    
    if pos_config:
        domain.append(('order_id.config_id.name', 'ilike', pos_config))
        
    lines = client.search_read(
        'pos.order.line',
        domain,
        ['product_id', 'qty', 'order_id', 'full_product_name']
    )
    
    if not lines:
        return f"No se encontraron productos en el período"
    
    # Get order dates
    order_ids = list(set([l['order_id'][0] for l in lines]))
    orders = client.search_read(
        'pos.order',
        [('id', 'in', order_ids)],
        ['id', 'date_order']
    )
    order_dates = {o['id']: o['date_order'] for o in orders}
    
    # Group by hour and product
    hourly_products = {h: {} for h in range(24)}
    product_totals = {}
    
    for line in lines:
        order_id = line['order_id'][0]
        date_str = order_dates.get(order_id)
        if not date_str:
            continue
            
        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        hour = dt.hour
        product_name = line['full_product_name'] or line['product_id'][1]
        qty = line['qty']
        
        if product_name not in hourly_products[hour]:
            hourly_products[hour][product_name] = 0
        hourly_products[hour][product_name] += qty
        
        if product_name not in product_totals:
            product_totals[product_name] = 0
        product_totals[product_name] += qty
    
    # Top 10 products overall
    top_products = sorted(product_totals.items(), key=lambda x: x[1], reverse=True)[:10]
    
    result = f"""
{'='*80}
🍳 ESTADÍSTICAS DE COCINA ({date_from} al {date_to})
{'='*80}

📊 TOP 10 PRODUCTOS MÁS PEDIDOS
{'-'*80}
{'Producto':<50} | {'Cantidad':>12}
{'-'*80}
"""
    for prod, qty in top_products:
        result += f"{prod[:50]:<50} | {qty:>12.0f}\n"
    
    result += f"""
{'-'*80}
⏰ PRODUCTOS POR HORA PICO
{'-'*80}
"""
    
    # Find peak hours (hours with most orders)
    hour_totals = {h: sum(products.values()) for h, products in hourly_products.items()}
    peak_hours = sorted(hour_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    for hour, total in peak_hours:
        if total == 0:
            continue
        result += f"\n🕐 {hour:02d}:00 - {hour:02d}:59 ({total:.0f} productos)\n"
        top_3 = sorted(hourly_products[hour].items(), key=lambda x: x[1], reverse=True)[:3]
        for prod, qty in top_3:
            result += f"   • {prod[:40]}: {qty:.0f}\n"
    
    result += f"\n{'='*80}\n"
    return result


async def get_tips_summary(date_from: str, date_to: str, pos_config: str | None = None) -> str:
    """Get tips summary by employee"""
    client = get_odoo_client()
    
    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())
    
    domain = [
        ('pos_order_id.date_order', '>=', client.datetime_to_odoo_format(dt_from)),
        ('pos_order_id.date_order', '<=', client.datetime_to_odoo_format(dt_to)),
        ('is_tip', '=', True)
    ]
    
    if pos_config:
        domain.append(('pos_order_id.config_id.name', 'ilike', pos_config))
        
    # Try to get tips from pos.payment (Odoo 16+)
    tips = client.search_read(
        'pos.payment',
        domain,
        ['amount', 'pos_order_id', 'session_id']
    )
    
    if not tips:
        # Alternative: check for tip products in order lines
        domain2 = [
            ('order_id.date_order', '>=', client.datetime_to_odoo_format(dt_from)),
            ('order_id.date_order', '<=', client.datetime_to_odoo_format(dt_to)),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            '|',
            ('product_id.name', 'ilike', 'propina'),
            ('product_id.name', 'ilike', 'tip')
        ]
        
        if pos_config:
            domain2.append(('order_id.config_id.name', 'ilike', pos_config))
            
        tip_lines = client.search_read(
            'pos.order.line',
            domain2,
            ['price_subtotal_incl', 'order_id']
        )
        
        if not tip_lines:
            return f"No se encontraron propinas en el período {date_from} al {date_to}"
            
        # Get employee from orders
        order_ids = list(set([l['order_id'][0] for l in tip_lines]))
        orders = client.search_read(
            'pos.order',
            [('id', 'in', order_ids)],
            ['id', 'employee_id']
        )
        order_employees = {o['id']: o['employee_id'] for o in orders}
        
        # Group by employee
        emp_tips = {}
        for line in tip_lines:
            order_id = line['order_id'][0]
            emp = order_employees.get(order_id)
            emp_name = emp[1] if emp else 'N/A'
            
            if emp_name not in emp_tips:
                emp_tips[emp_name] = {'amount': 0, 'count': 0}
            emp_tips[emp_name]['amount'] += line['price_subtotal_incl']
            emp_tips[emp_name]['count'] += 1
    else:
        # Process tips from payments
        order_ids = list(set([t['pos_order_id'][0] for t in tips if t['pos_order_id']]))
        orders = client.search_read(
            'pos.order',
            [('id', 'in', order_ids)],
            ['id', 'employee_id']
        )
        order_employees = {o['id']: o['employee_id'] for o in orders}
        
        emp_tips = {}
        for tip in tips:
            if not tip['pos_order_id']:
                continue
            order_id = tip['pos_order_id'][0]
            emp = order_employees.get(order_id)
            emp_name = emp[1] if emp else 'N/A'
            
            if emp_name not in emp_tips:
                emp_tips[emp_name] = {'amount': 0, 'count': 0}
            emp_tips[emp_name]['amount'] += tip['amount']
            emp_tips[emp_name]['count'] += 1
    
    total_tips = sum(e['amount'] for e in emp_tips.values())
    total_count = sum(e['count'] for e in emp_tips.values())
    
    sorted_tips = sorted(emp_tips.items(), key=lambda x: x[1]['amount'], reverse=True)
    
    result = f"""
{'='*80}
💰 RESUMEN DE PROPINAS ({date_from} al {date_to})
{'='*80}

📊 TOTAL GENERAL
{'-'*80}
Total propinas:    ${total_tips:,.2f}
Cantidad:          {total_count}
Promedio:          ${total_tips/total_count if total_count > 0 else 0:,.2f}

👨‍🍳 PROPINAS POR EMPLEADO
{'-'*80}
{'Empleado':<35} | {'Cantidad':>10} | {'Total':>15} | {'Promedio':>12}
{'-'*80}
"""
    
    for emp, data in sorted_tips:
        avg = data['amount'] / data['count'] if data['count'] > 0 else 0
        result += f"{emp[:35]:<35} | {data['count']:>10} | ${data['amount']:>14,.2f} | ${avg:>11,.2f}\n"
    
    result += f"\n{'='*80}\n"
    return result


async def get_low_stock_products(threshold: int = 10, category: str | None = None) -> str:
    """Get products with low stock available in POS"""
    client = get_odoo_client()
    
    domain = [
        ('available_in_pos', '=', True),
        ('type', '=', 'product'),  # Only storable products
        ('qty_available', '<=', threshold),
        ('qty_available', '>', 0)  # Not completely out of stock
    ]
    
    if category:
        domain.append(('categ_id.name', 'ilike', category))
        
    products = client.search_read(
        'product.product',
        domain,
        ['name', 'default_code', 'qty_available', 'categ_id', 'list_price', 'virtual_available'],
        order='qty_available asc',
        limit=50
    )
    
    # Also get out of stock products
    out_of_stock_domain = [
        ('available_in_pos', '=', True),
        ('type', '=', 'product'),
        ('qty_available', '<=', 0)
    ]
    
    if category:
        out_of_stock_domain.append(('categ_id.name', 'ilike', category))
        
    out_of_stock = client.search_read(
        'product.product',
        out_of_stock_domain,
        ['name', 'default_code', 'categ_id'],
        limit=20
    )
    
    result = f"""
{'='*80}
📦 PRODUCTOS CON STOCK BAJO (Umbral: {threshold} unidades)
{'='*80}

"""
    
    if out_of_stock:
        result += f"""⚠️ AGOTADOS ({len(out_of_stock)} productos)
{'-'*80}
"""
        for p in out_of_stock[:10]:
            categ = p['categ_id'][1] if p['categ_id'] else 'N/A'
            code = p.get('default_code') or '-'
            result += f"❌ {p['name'][:40]} | {code} | {categ[:20]}\n"
        if len(out_of_stock) > 10:
            result += f"   ... y {len(out_of_stock) - 10} más\n"
        result += "\n"
    
    if products:
        result += f"""🔶 STOCK BAJO ({len(products)} productos)
{'-'*80}
{'Producto':<35} | {'Código':<12} | {'Stock':>8} | {'Precio':>12}
{'-'*80}
"""
        for p in products:
            code = p.get('default_code') or '-'
            result += f"{p['name'][:35]:<35} | {code:<12} | {p['qty_available']:>8.0f} | ${p['list_price']:>11,.2f}\n"
    else:
        result += "✅ No hay productos con stock bajo\n"
    
    result += f"\n{'='*80}\n"
    return result


async def get_invoices_summary(date_from: str, date_to: str, state: str | None = None) -> str:
    """Get invoices summary for a period"""
    client = get_odoo_client()
    
    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to, "%Y-%m-%d")
    dt_to = datetime.combine(dt_to.date(), datetime.max.time())
    
    domain = [
        ('invoice_date', '>=', date_from),
        ('invoice_date', '<=', date_to),
        ('move_type', 'in', ['out_invoice', 'out_refund'])  # Customer invoices and credit notes
    ]
    
    if state:
        domain.append(('state', '=', state))
        
    invoices = client.search_read(
        'account.move',
        domain,
        ['name', 'invoice_date', 'partner_id', 'amount_total', 'amount_residual', 
         'state', 'move_type', 'currency_id']
    )
    
    if not invoices:
        return f"No se encontraron facturas en el período {date_from} al {date_to}"
    
    # Group by state
    by_state = {}
    total_invoiced = 0
    total_pending = 0
    total_credit_notes = 0
    
    for inv in invoices:
        st = inv['state']
        if st not in by_state:
            by_state[st] = {'count': 0, 'total': 0, 'pending': 0}
        by_state[st]['count'] += 1
        
        if inv['move_type'] == 'out_invoice':
            by_state[st]['total'] += inv['amount_total']
            by_state[st]['pending'] += inv['amount_residual']
            total_invoiced += inv['amount_total']
            total_pending += inv['amount_residual']
        else:  # Credit note
            total_credit_notes += inv['amount_total']
    
    result = f"""
{'='*80}
🧾 RESUMEN DE FACTURAS ({date_from} al {date_to})
{'='*80}

📊 TOTALES GENERALES
{'-'*80}
Total Facturado:      ${total_invoiced:,.2f}
Notas de Crédito:     ${total_credit_notes:,.2f}
Neto:                 ${total_invoiced - total_credit_notes:,.2f}
Pendiente de Cobro:   ${total_pending:,.2f}
Total Facturas:       {len(invoices)}

📋 POR ESTADO
{'-'*80}
{'Estado':<15} | {'Cantidad':>10} | {'Total':>18} | {'Pendiente':>15}
{'-'*80}
"""
    
    state_names = {'draft': 'Borrador', 'posted': 'Publicada', 'cancel': 'Cancelada'}
    for st, data in by_state.items():
        st_name = state_names.get(st, st)
        result += f"{st_name:<15} | {data['count']:>10} | ${data['total']:>17,.2f} | ${data['pending']:>14,.2f}\n"
    
    # Top 5 invoices
    top_invoices = sorted([i for i in invoices if i['move_type'] == 'out_invoice'], 
                         key=lambda x: x['amount_total'], reverse=True)[:5]
    
    result += f"""
📈 TOP 5 FACTURAS
{'-'*80}
{'Número':<20} | {'Cliente':<25} | {'Monto':>15}
{'-'*80}
"""
    for inv in top_invoices:
        partner = inv['partner_id'][1][:25] if inv['partner_id'] else 'N/A'
        result += f"{inv['name']:<20} | {partner:<25} | ${inv['amount_total']:>14,.2f}\n"
    
    result += f"\n{'='*80}\n"
    return result


async def get_invoice_details(invoice_number: str | None = None, invoice_id: int | None = None) -> str:
    """Get complete details of a specific invoice"""
    client = get_odoo_client()
    
    if not invoice_number and not invoice_id:
        return "Debe proporcionar invoice_number o invoice_id"
    
    domain = [('move_type', 'in', ['out_invoice', 'out_refund'])]
    if invoice_id:
        domain.append(('id', '=', invoice_id))
    elif invoice_number:
        domain.append(('name', 'ilike', invoice_number))
    
    invoices = client.search_read(
        'account.move',
        domain,
        ['name', 'invoice_date', 'partner_id', 'amount_total', 'amount_residual',
         'amount_untaxed', 'amount_tax', 'state', 'move_type', 'ref', 'narration',
         'invoice_line_ids', 'payment_state', 'currency_id', 'invoice_user_id'],
        limit=1
    )
    
    if not invoices:
        return f"No se encontró la factura '{invoice_number or invoice_id}'"
    
    inv = invoices[0]
    
    # Get invoice lines
    lines = client.search_read(
        'account.move.line',
        [('move_id', '=', inv['id']), ('display_type', '=', 'product')],
        ['name', 'quantity', 'price_unit', 'discount', 'price_subtotal', 'product_id', 'tax_ids']
    )
    
    move_type_names = {'out_invoice': 'Factura de Cliente', 'out_refund': 'Nota de Crédito'}
    state_names = {'draft': 'Borrador', 'posted': 'Publicada', 'cancel': 'Cancelada'}
    payment_names = {'not_paid': 'No Pagada', 'partial': 'Pago Parcial', 'paid': 'Pagada', 
                     'in_payment': 'En Proceso', 'reversed': 'Reversada'}
    
    partner = inv['partner_id'][1] if inv['partner_id'] else 'N/A'
    date_str = inv['invoice_date'] or 'Sin fecha'
    user = inv['invoice_user_id'][1] if inv['invoice_user_id'] else 'N/A'
    currency = inv['currency_id'][1] if inv['currency_id'] else 'COP'
    
    result = f"""
{'='*80}
🧾 DETALLE DE FACTURA: {inv['name']}
{'='*80}

📋 INFORMACIÓN GENERAL
{'-'*80}
Tipo:             {move_type_names.get(inv['move_type'], inv['move_type'])}
Fecha:            {date_str}
Cliente:          {partner}
Referencia:       {inv.get('ref') or 'N/A'}
Vendedor:         {user}
Estado:           {state_names.get(inv['state'], inv['state'])}
Estado de Pago:   {payment_names.get(inv['payment_state'], inv['payment_state'])}
Moneda:           {currency}

💰 MONTOS
{'-'*80}
Subtotal:         ${inv['amount_untaxed']:,.2f}
Impuestos:        ${inv['amount_tax']:,.2f}
TOTAL:            ${inv['amount_total']:,.2f}
Pendiente:        ${inv['amount_residual']:,.2f}

📦 LÍNEAS DE FACTURA ({len(lines)} items)
{'-'*80}
{'Producto':<35} | {'Cant':>6} | {'P.Unit':>12} | {'Subtotal':>12}
{'-'*80}
"""
    for line in lines:
        product = line['product_id'][1][:35] if line['product_id'] else line['name'][:35]
        result += f"{product:<35} | {line['quantity']:>6.2f} | ${line['price_unit']:>11,.2f} | ${line['price_subtotal']:>11,.2f}\n"
    
    result += f"\n{'='*80}\n"
    return result


async def search_invoices(query: str, state: str | None = None, limit: int = 20) -> str:
    """Search invoices by customer, number or reference"""
    client = get_odoo_client()
    
    domain = [
        ('move_type', 'in', ['out_invoice', 'out_refund']),
        '|', '|',
        ('name', 'ilike', query),
        ('partner_id.name', 'ilike', query),
        ('ref', 'ilike', query)
    ]
    
    if state:
        domain.append(('state', '=', state))
    
    invoices = client.search_read(
        'account.move',
        domain,
        ['name', 'invoice_date', 'partner_id', 'amount_total', 'amount_residual', 
         'state', 'move_type', 'payment_state'],
        order='invoice_date desc',
        limit=limit
    )
    
    if not invoices:
        return f"No se encontraron facturas para '{query}'"
    
    type_icons = {'out_invoice': '🧾', 'out_refund': '↩️'}
    
    result = f"""
{'='*90}
🔍 BÚSQUEDA DE FACTURAS: "{query}"
{'='*90}

{'Tipo':<4} | {'Número':<20} | {'Fecha':<12} | {'Cliente':<25} | {'Total':>12} | {'Pend':>10}
{'-'*90}
"""
    for inv in invoices:
        icon = type_icons.get(inv['move_type'], '📄')
        partner = inv['partner_id'][1][:25] if inv['partner_id'] else 'N/A'
        date = inv['invoice_date'] or 'N/A'
        result += f"{icon:<4} | {inv['name']:<20} | {date:<12} | {partner:<25} | ${inv['amount_total']:>11,.2f} | ${inv['amount_residual']:>9,.2f}\n"
    
    result += f"\n{'='*90}\nTotal: {len(invoices)}\n"
    return result


async def get_customer_invoices(customer_name: str, date_from: str | None = None, 
                                 date_to: str | None = None, include_paid: bool = True) -> str:
    """Get all invoices for a specific customer"""
    client = get_odoo_client()
    
    # Find customer
    partners = client.search_read(
        'res.partner',
        [('name', 'ilike', customer_name)],
        ['name', 'email', 'phone', 'vat'],
        limit=5
    )
    
    if not partners:
        return f"No se encontró el cliente '{customer_name}'"
    
    partner = partners[0]
    
    domain = [
        ('partner_id', '=', partner['id']),
        ('move_type', 'in', ['out_invoice', 'out_refund'])
    ]
    
    if date_from:
        domain.append(('invoice_date', '>=', date_from))
    if date_to:
        domain.append(('invoice_date', '<=', date_to))
    if not include_paid:
        domain.append(('amount_residual', '>', 0))
    
    invoices = client.search_read(
        'account.move',
        domain,
        ['name', 'invoice_date', 'amount_total', 'amount_residual', 'state', 
         'move_type', 'payment_state'],
        order='invoice_date desc'
    )
    
    # Calculate totals
    total_invoiced = sum(i['amount_total'] for i in invoices if i['move_type'] == 'out_invoice')
    total_credits = sum(i['amount_total'] for i in invoices if i['move_type'] == 'out_refund')
    total_pending = sum(i['amount_residual'] for i in invoices)
    
    result = f"""
{'='*90}
👤 FACTURAS DE CLIENTE: {partner['name']}
{'='*90}

📋 CLIENTE
{'-'*90}
Nombre:      {partner['name']}
NIT/RUT:     {partner.get('vat') or 'N/A'}
Email:       {partner.get('email') or 'N/A'}
Teléfono:    {partner.get('phone') or 'N/A'}

💰 RESUMEN
{'-'*90}
Total Facturado:    ${total_invoiced:,.2f}
Notas de Crédito:   ${total_credits:,.2f}
Neto:               ${total_invoiced - total_credits:,.2f}
Pendiente de Pago:  ${total_pending:,.2f}
Cantidad Facturas:  {len(invoices)}

📄 DETALLE
{'-'*90}
{'Número':<20} | {'Fecha':<12} | {'Total':>12} | {'Pendiente':>12} | {'Estado':<10}
{'-'*90}
"""
    
    state_names = {'draft': 'Borrador', 'posted': 'Publicada', 'cancel': 'Cancelada'}
    type_prefix = {'out_invoice': '', 'out_refund': '(NC) '}
    
    for inv in invoices:
        prefix = type_prefix.get(inv['move_type'], '')
        name = f"{prefix}{inv['name']}"[:20]
        date = inv['invoice_date'] or 'N/A'
        state = state_names.get(inv['state'], inv['state'])
        result += f"{name:<20} | {date:<12} | ${inv['amount_total']:>11,.2f} | ${inv['amount_residual']:>11,.2f} | {state:<10}\n"
    
    result += f"\n{'='*90}\n"
    return result


async def get_session_reconciliation(session_name: str | None = None, 
                                     date_from: str | None = None, 
                                     date_to: str | None = None) -> str:
    """Get POS session reconciliation (cash control differences)"""
    client = get_odoo_client()
    
    domain = [('state', 'in', ['closed', 'closing_control'])]
    
    if session_name:
        domain.append(('name', 'ilike', session_name))
    
    if date_from:
        domain.append(('start_at', '>=', date_from + ' 00:00:00'))
    if date_to:
        domain.append(('start_at', '<=', date_to + ' 23:59:59'))
    
    # If no filters, get last 10 sessions
    sessions = client.search_read(
        'pos.session',
        domain,
        ['name', 'start_at', 'stop_at', 'user_id', 'config_id',
         'cash_register_balance_start', 'cash_register_balance_end_real',
         'total_payments_amount', 'state'],
        order='start_at desc',
        limit=20 if not session_name else 100
    )
    
    if not sessions:
        return "No se encontraron sesiones cerradas con los filtros especificados"
    
    # Get payment details for each session
    session_ids = [s['id'] for s in sessions]
    
    payments = client.search_read(
        'pos.payment',
        [('session_id', 'in', session_ids)],
        ['session_id', 'payment_method_id', 'amount']
    )
    
    # Group payments by session and method
    session_payments = {}
    for p in payments:
        sid = p['session_id'][0]
        if sid not in session_payments:
            session_payments[sid] = {'cash': 0, 'other': 0, 'total': 0}
        
        method_name = p['payment_method_id'][1].lower() if p['payment_method_id'] else ''
        if 'efectivo' in method_name or 'cash' in method_name:
            session_payments[sid]['cash'] += p['amount']
        else:
            session_payments[sid]['other'] += p['amount']
        session_payments[sid]['total'] += p['amount']
    
    result = f"""
{'='*80}
💰 CUADRE DE CAJA - SESIONES POS
{'='*80}

"""
    
    total_diff = 0
    sessions_with_diff = 0
    
    for s in sessions:
        sid = s['id']
        sp = session_payments.get(sid, {'cash': 0, 'other': 0, 'total': 0})
        
        # Calculate expected vs real for cash
        cash_start = s.get('cash_register_balance_start') or 0
        cash_end_real = s.get('cash_register_balance_end_real') or 0
        cash_expected = cash_start + sp['cash']
        cash_diff = cash_end_real - cash_expected
        
        pos_name = s['config_id'][1] if s['config_id'] else 'N/A'
        user = s['user_id'][1] if s['user_id'] else 'N/A'
        start = utc_to_bogota(s['start_at'])[:16] if s['start_at'] else 'N/A'
        
        if cash_diff != 0:
            sessions_with_diff += 1
            total_diff += cash_diff
            
        diff_indicator = "✅" if abs(cash_diff) < 1 else ("⚠️" if abs(cash_diff) < 1000 else "❌")
        
        result += f"""
{diff_indicator} {s['name']} ({pos_name})
{'-'*80}
   Usuario:          {user}
   Inicio:           {start}
   Apertura Caja:    ${cash_start:,.2f}
   Ventas Efectivo:  ${sp['cash']:,.2f}
   Esperado:         ${cash_expected:,.2f}
   Real:             ${cash_end_real:,.2f}
   Diferencia:       ${cash_diff:,.2f} {'SOBRANTE' if cash_diff > 0 else 'FALTANTE' if cash_diff < 0 else 'OK'}
   Otros Pagos:      ${sp['other']:,.2f}
"""
    
    result += f"""
{'='*80}
📊 RESUMEN
{'-'*80}
Sesiones analizadas:     {len(sessions)}
Sesiones con diferencia: {sessions_with_diff}
Diferencia total:        ${total_diff:,.2f}
{'='*80}
"""
    return result


async def get_session_details(session_id: int | None = None, session_name: str | None = None) -> str:
    """Get complete details for a specific POS session"""
    client = get_odoo_client()
    
    domain = []
    if session_id:
        domain = [('id', '=', session_id)]
    elif session_name:
        domain = [('name', 'ilike', session_name)]
    else:
        return "Debe proporcionar session_id o session_name"
        
    session = client.search_read(
        'pos.session',
        domain,
        ['name', 'start_at', 'stop_at', 'user_id', 'config_id', 'state',
         'cash_register_balance_start', 'cash_register_balance_end_real', 
         'total_payments_amount', 'order_ids'],
        limit=1
    )
    
    if not session:
        return f"No se encontró la sesión"
        
    s = session[0]
    
    # Get payment details
    payments = client.search_read(
        'pos.payment',
        [('session_id', '=', s['id'])],
        ['payment_method_id', 'amount']
    )
    
    pm_summary = {}
    for p in payments:
        pm_name = p['payment_method_id'][1]
        pm_summary[pm_name] = pm_summary.get(pm_name, 0) + p['amount']
        
    # Get orders summary
    order_ids = s['order_ids']
    order_count = len(order_ids)
    
    result = f"""
{'='*80}
📋 DETALLES DE SESIÓN: {s['name']}
{'='*80}

📍 INFO GENERAL
{'-'*80}
Estado:       {s['state']}
POS:          {s['config_id'][1]}
Responsable:  {s['user_id'][1]}
Inicio:       {utc_to_bogota(s['start_at']) if s['start_at'] else 'N/A'} (Bogotá)
Cierre:       {utc_to_bogota(s['stop_at']) if s['stop_at'] else 'En curso'}

💰 BALANCE
{'-'*80}
Apertura Caja:   ${s['cash_register_balance_start']:,.2f}
Total Ventas:    ${s['total_payments_amount']:,.2f}
Cierre Real:     ${s['cash_register_balance_end_real']:,.2f}
Diferencia:      ${s['cash_register_balance_end_real'] - (s['cash_register_balance_start'] + pm_summary.get('Efectivo', 0)):,.2f}

💳 MÉTODOS DE PAGO
{'-'*80}
"""
    for pm, amount in pm_summary.items():
        result += f"{pm:<20} | ${amount:,.2f}\n"
        
    result += f"\nTotal Órdenes: {order_count}\n"
    result += f"{'='*80}\n"
    
    return result


async def get_sessions_by_cashier(cashier_name: str, limit: int = 10) -> str:
    """Get session history by cashier"""
    client = get_odoo_client()
    
    sessions = client.search_read(
        'pos.session',
        [('user_id.name', 'ilike', cashier_name), ('state', 'in', ['closed', 'opened'])],
        ['name', 'start_at', 'stop_at', 'config_id', 'total_payments_amount', 'state'],
        order='start_at desc',
        limit=limit
    )
    
    if not sessions:
        return f"No se encontraron sesiones para el usuario '{cashier_name}'"
        
    result = f"""
{'='*80}
👤 HISTORIAL DE SESIONES: {cashier_name}
{'='*80}

{'Sesión':<20} | {'Fecha':<16} | {'Estado':<10} | {'Ventas':>15}
{'-'*80}
"""
    
    total_sales = 0
    for s in sessions:
        total_sales += s['total_payments_amount']
        date_str = utc_to_bogota(s['start_at'])[:16]  # Bogotá
        result += f"{s['name']:<20} | {date_str:<16} | {s['state']:<10} | ${s['total_payments_amount']:>14,.2f}\n"
        
    result += f"{'-'*80}\n"
    result += f"Total Ventas ({len(sessions)} sesiones): ${total_sales:,.2f}\n"
    result += f"{'='*80}\n"
    
    return result


async def get_session_vs_session(session1_name: str, session2_name: str) -> str:
    """Compare two POS sessions"""
    client = get_odoo_client()
    
    sessions = client.search_read(
        'pos.session',
        ['|', ('name', 'ilike', session1_name), ('name', 'ilike', session2_name)],
        ['name', 'start_at', 'total_payments_amount', 'order_ids', 'user_id'],
        limit=2
    )
    
    if len(sessions) < 2:
        return "No se encontraron ambas sesiones para comparar"
        
    s1 = sessions[0]
    s2 = sessions[1]
    
    # Calculate order counts
    s1_orders = len(s1['order_ids'])
    s2_orders = len(s2['order_ids'])
    
    # Averages
    s1_avg = s1['total_payments_amount'] / s1_orders if s1_orders else 0
    s2_avg = s2['total_payments_amount'] / s2_orders if s2_orders else 0
    
    result = f"""
{'='*80}
🆚 COMPARATIVA DE SESIONES
{'='*80}

METRICAS            | {s1['name']:<25} | {s2['name']:<25}
{'-'*80}
Responsable         | {s1['user_id'][1][:25]:<25} | {s2['user_id'][1][:25]:<25}
Fecha               | {utc_to_bogota(s1['start_at'])[:16]:<25} | {utc_to_bogota(s2['start_at'])[:16]:<25}
Ventas Totales      | ${s1['total_payments_amount']:<24,.2f} | ${s2['total_payments_amount']:<24,.2f}
Total Órdenes       | {s1_orders:<25} | {s2_orders:<25}
Ticket Promedio     | ${s1_avg:<24,.2f} | ${s2_avg:<24,.2f}
{'='*80}
"""
    return result


async def get_busiest_sessions(date_from: str, date_to: str, metric: str = 'amount', limit: int = 5) -> str:
    """Get top sessions by sales or orders"""
    client = get_odoo_client()
    
    sessions = client.search_read(
        'pos.session',
        [('start_at', '>=', date_from + ' 00:00:00'),
         ('start_at', '<=', date_to + ' 23:59:59'),
         ('state', '=', 'closed')],
        ['name', 'start_at', 'user_id', 'total_payments_amount', 'order_ids', 'config_id'],
        order='total_payments_amount desc' if metric == 'amount' else 'id desc', # Cant sort by len(order_ids) directly in search
        limit=50 # Get more then sort in python for orders
    )
    
    if metric == 'orders':
        sessions.sort(key=lambda x: len(x['order_ids']), reverse=True)
        sessions = sessions[:limit]
    else:
        sessions = sessions[:limit]
        
    metric_label = "VENTAS" if metric == 'amount' else "ÓRDENES"
    
    result = f"""
{'='*80}
🏆 TOP SESIONES POR {metric_label} ({date_from} al {date_to})
{'='*80}

{'Sesión':<20} | {'Usuario':<20} | {'Fecha':<12} | {'Ventas':>12} | {'Órdenes':>8}
{'-'*80}
"""
    
    for s in sessions:
        user = s['user_id'][1][:20] if s['user_id'] else 'N/A'
        date = utc_to_bogota(s['start_at'])[:16]  # Bogotá
        orders = len(s['order_ids'])
        result += f"{s['name']:<20} | {user:<20} | {date:<12} | ${s['total_payments_amount']:>11,.0f} | {orders:>8}\n"
        
    result += f"\n{'='*80}\n"
    return result


async def get_product_details(product_name: str) -> str:
    """Get full details of a product"""
    client = get_odoo_client()
    
    products = client.search_read(
        'product.product',
        ['|', ('name', 'ilike', product_name), ('default_code', 'ilike', product_name)],
        ['name', 'default_code', 'list_price', 'standard_price', 'qty_available', 
         'categ_id', 'type', 'uom_id', 'taxes_id']
    )
    
    if not products:
        return f"No se encontró el producto '{product_name}'"
        
    p = products[0] # Return first match
    
    result = f"""
{'='*60}
📦 DETALLES DEL PRODUCTO
{'='*60}
Nombre:       {p['name']}
Referencia:   {p.get('default_code') or 'N/A'}
Categoría:    {p['categ_id'][1] if p['categ_id'] else 'N/A'}
Tipo:         {p['type']}
Unidad:       {p['uom_id'][1] if p['uom_id'] else 'N/A'}

💰 PRECIOS
{'-'*60}
Precio Venta: ${p['list_price']:,.2f}
Costo:        ${p['standard_price']:,.2f}
Impuestos:    {len(p['taxes_id'])} impuestos aplicados

📊 INVENTARIO
{'-'*60}
Stock Mano:   {p['qty_available']} unidades
{'='*60}
"""
    return result


async def search_products(query: str, category: str | None = None, limit: int = 20) -> str:
    """Search products by name, code or category"""
    client = get_odoo_client()
    
    domain = ['|', ('name', 'ilike', query), ('default_code', 'ilike', query)]
    
    if category:
        domain = ['&'] + domain + [('categ_id.name', 'ilike', category)]
        
    products = client.search_read(
        'product.product',
        domain,
        ['name', 'default_code', 'list_price', 'qty_available', 'categ_id'],
        limit=limit
    )
    
    if not products:
        return f"No se encontraron productos con '{query}'"
        
    result = f"""
{'='*80}
🔍 RESULTADOS BÚSQUEDA: "{query}"
{'='*80}
{'Código':<12} | {'Nombre':<35} | {'Precio':>12} | {'Stock':>8}
{'-'*80}
"""
    for p in products:
        code = p.get('default_code') or '-'
        result += f"{code:<12} | {p['name'][:35]:<35} | ${p['list_price']:>11,.2f} | {p['qty_available']:>8.0f}\n"
        
    result += f"\n{'='*80}\n"
    return result


async def update_product_price(product_name: str, new_price: float) -> str:
    """Update the list price of a product"""
    client = get_odoo_client()
    
    products = client.search_read(
        'product.product',
        ['|', ('name', 'ilike', product_name), ('default_code', 'ilike', product_name)],
        ['name', 'list_price']
    )
    
    if not products:
        return f"No se encontró el producto '{product_name}'"
        
    # Logic to select best match
    target_product = None
    if len(products) == 1:
        target_product = products[0]
    else:
        # Try exact match
        exact = [p for p in products if p['name'].lower() == product_name.lower()]
        if len(exact) == 1:
            target_product = exact[0]
        else:
            # List options
            msg = f"Múltiples productos encontrados para '{product_name}':\n"
            for p in products[:5]:
                msg += f"- {p['name']} (ID: {p['id']}, Precio: {p['list_price']})\n"
            msg += "Por favor sea más específico con el nombre o use la referencia."
            return msg
            
    # Execute update
    try:
        # Odoo write method via client.execute: model, method, args...
        result = client.execute(
            'product.product', 
            'write',
            [target_product['id']],
            {'list_price': new_price}
        )
        
        # Verify update
        updated = client.search_read('product.product', [('id', '=', target_product['id'])], ['list_price'])[0]
        
        return f"""
✅ PRECIO ACTUALIZADO
{'='*40}
Producto:        {target_product['name']}
Precio Anterior: ${target_product['list_price']:,.2f}
Precio Nuevo:    ${updated['list_price']:,.2f}
{'='*40}
"""
    except Exception as e:
        return f"❌ Error al actualizar precio: {str(e)}"

    """Async main entry point for the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


def main():
    """Main entry point (wrapper for CLI)"""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
S