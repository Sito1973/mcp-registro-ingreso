import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def get_data():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    output_file = "result.txt"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Iniciando...\n")
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write("Sesion inicializada.\n")
                
                # Buscar Santiago
                result = await session.call_tool("consultar_empleados", {"activos_solo": True})
                data = json.loads(result.content[0].text)
                
                emp_id = None
                emp_nombre = ""
                
                for emp in data["empleados"]:
                    full_name = emp["nombre_completo"].upper()
                    if "SANTIAGO" in full_name and "CONTRERAS" in full_name:
                        emp_id = emp["id"]
                        emp_nombre = emp["nombre_completo"]
                        break
                
                with open(output_file, "a", encoding="utf-8") as f:
                    if emp_id:
                        f.write(f"Empleado encontrado: {emp_nombre} (ID: {emp_id})\n")
                        
                        # Consultar registros
                        reg_result = await session.call_tool(
                            "consultar_registros_fecha",
                            {"fecha": "2026-01-02", "empleado_id": emp_id}
                        )
                        reg_data = json.loads(reg_result.content[0].text)
                        
                        f.write(f"Total registros: {reg_data['total_registros']}\n")
                        for reg in reg_data["registros"]:
                            f.write(f"- {reg['hora_registro']} | {reg['tipo_registro']} | {reg['punto_trabajo']}\n")
                    else:
                        f.write("No se encontro a Santiago Contreras.\n")

    except Exception as e:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"ERROR: {str(e)}\n")

if __name__ == "__main__":
    asyncio.run(get_data())
