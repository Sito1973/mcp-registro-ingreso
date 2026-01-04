import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def check_salgado_date():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # 1. Buscar Salgado
                print("Buscando a Salgado...")
                result = await session.call_tool("buscar_empleado", {"termino": "SALGADO"})
                data = json.loads(result.content[0].text)
                
                if data["resultados"] == 0:
                    print("No se encontró a Salgado.")
                    return
                
                emp = data["empleados"][0]
                emp_id = emp["id"]
                print(f"Encontrado: {emp['nombre_completo']} ({emp_id})")
                
                # 2. Consultar registros para el 2 de diciembre
                fecha = "2025-12-02"
                print(f"\nConsultando registros para {fecha}...")
                reg_result = await session.call_tool(
                    "consultar_registros_fecha",
                    {"fecha": fecha, "empleado_id": emp_id}
                )
                reg_data = json.loads(reg_result.content[0].text)
                print(f"Total registros encontrados: {reg_data.get('total_registros', 0)}")
                
                for reg in reg_data.get("registros", []):
                    print(f"- {reg['hora_registro']} | {reg['tipo_registro']} | {reg['punto_trabajo']}")

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_salgado_date())
