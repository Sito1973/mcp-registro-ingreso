import asyncio
import json
import httpx
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def test_remote_mcp():
    # URL del servidor desplegado en Easypanel
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    
    print(f"Conectando a {url}...")
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. Inicializar
                print("Inicializando sesión...")
                await session.initialize()
                
                # 2. Listar herramientas
                # print("\n--- Herramientas Disponibles ---")
                # tools_result = await session.list_tools()
                # for tool in tools_result.tools:
                #     print(f"- {tool.name}: {tool.description[:60]}...")
                
                # 3. Buscar empleado "SANTIAGO CONTRERAS"
                # 3. Buscar empleado "SANTIAGO CONTRERAS" (Usando listado y filtro python para mayor seguridad)
                print("\n--- Buscando 'SANTIAGO CONTRERAS' en lista general ---")
                search_result = await session.call_tool(
                    "consultar_empleados", 
                    {"activos_solo": True}
                )
                search_data = json.loads(search_result.content[0].text)
                
                empleado_encontrado = None
                for emp in search_data["empleados"]:
                    nombre_full = emp["nombre_completo"].upper()
                    if "SANTIAGO" in nombre_full and "CONTRERAS" in nombre_full:
                        empleado_encontrado = emp
                        break
                
                if empleado_encontrado:
                    emp_id = empleado_encontrado["id"]
                    print(f"✅ Encontrado: {empleado_encontrado['nombre_completo']} (ID: {emp_id})")
                    
                    # 4. Consultar registros del 2 de Enero 2026
                    print(f"\n--- Consultando registros del 2026-01-02 ---")
                    records_result = await session.call_tool(
                        "consultar_registros_fecha",
                        {
                            "fecha": "2026-01-02",
                            "empleado_id": emp_id
                        }
                    )
                    records_data = json.loads(records_result.content[0].text)
                    print(f"Total registros: {records_data['total_registros']}")
                    for reg in records_data["registros"]:
                        print(f"- {reg['hora_registro']} | {reg['tipo_registro']} | {reg['punto_trabajo']}")
                else:
                    print("❌ No se encontró al empleado.")

    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_remote_mcp())
