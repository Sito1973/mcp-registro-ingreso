import asyncio
import json
import traceback
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
                        f.write(f"Consultando horas del 2025-12-29 al 2026-01-02\n\n")
                        
                        dates = [
                            "2025-12-29", "2025-12-30", "2025-12-31",
                            "2026-01-01", "2026-01-02"
                        ]
                        
                        total_horas = 0
                        
                        for fecha in dates:
                            f.write(f"--- Fecha: {fecha} ---\n")
                            horas_result = await session.call_tool(
                                "calcular_horas_trabajadas_dia",
                                {"empleado_id": emp_id, "fecha": fecha}
                            )
                            horas_data = json.loads(horas_result.content[0].text)
                            
                            if "error" in horas_data:
                                f.write(f"Error: {horas_data['error']}\n")
                            elif "mensaje" in horas_data:
                                f.write(f"{horas_data['mensaje']}\n")
                            else:
                                h_trabajadas = horas_data.get("horas_trabajadas", 0)
                                h_ord = horas_data.get("horas_ordinarias", 0)
                                h_ext = horas_data.get("horas_extra_diurna", 0) + horas_data.get("horas_extra_nocturna", 0)
                                
                                total_horas += h_trabajadas
                                f.write(f"Horas Trabajadas: {h_trabajadas} (Ord: {h_ord}, Extras: {h_ext})\n")
                                for reg in horas_data.get("registros", []):
                                    f.write(f"  {reg['hora']} - {reg['tipo']}\n")
                            f.write("\n")
                            
                        f.write(f"TOTAL HORAS EN EL PERIODO: {round(total_horas, 2)}\n")
                    else:
                        f.write("No se encontro a Santiago Contreras.\n")

    except Exception as e:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"ERROR: {str(e)}\n")
            f.write(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(get_data())
