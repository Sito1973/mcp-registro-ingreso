import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def diagnose_mismatch():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 1. Get Employee details
                print("Consultando detalle de Salgado...")
                result = await session.call_tool("buscar_empleado", {"termino": "SALGADO"})
                emp_data = json.loads(result.content[0].text)
                emp = emp_data["empleados"][0]
                emp_id = emp["id"]
                emp_punto = emp.get("punto_trabajo", "N/A")
                print(f"Empleado: {emp['nombre_completo']}")
                print(f"Punto en tabla 'empleados': '{emp_punto}'")
                
                # 2. Get Records for 2025-12-02 (NO RESTAURANT FILTER)
                print(f"\nConsultando registros 2025-12-02 (SIN filtro de restaurante)...")
                reg_result = await session.call_tool(
                    "consultar_registros_fecha",
                    {"fecha": "2025-12-02", "empleado_id": emp_id}
                )
                reg_data = json.loads(reg_result.content[0].text)
                
                if reg_data["total_registros"] > 0:
                    first_reg = reg_data["registros"][0]
                    reg_punto = first_reg.get("punto_trabajo", "N/A")
                    print(f"Punto en tabla 'registros': '{reg_punto}'")
                    
                    if emp_punto != reg_punto:
                        print(f"\n⚠️ ¡Mismatched detectado!")
                        print(f"Si el LLM filtra por '{emp_punto}', no encontrará registros porque en la base de datos dice '{reg_punto}'.")
                else:
                    print("No se encontraron registros.")

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(diagnose_mismatch())
