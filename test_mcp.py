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
                print("\n--- Herramientas Disponibles ---")
                tools_result = await session.list_tools()
                for tool in tools_result.tools:
                    print(f"- {tool.name}: {tool.description[:60]}...")
                
                # 3. Probar una consulta real (Consultar empleados activos)
                print("\n--- Probando 'consultar_empleados' (Verifica BD) ---")
                response = await session.call_tool(
                    "consultar_empleados", 
                    {"activos_solo": True}
                )
                
                # La respuesta viene como una lista de TextContent
                content = response.content[0].text
                data = json.loads(content)
                
                if "error" in data:
                    print(f"❌ Error en la herramienta: {data['error']}")
                else:
                    total = data.get("total", 0)
                    print(f"✅ Éxito! Se encontraron {total} empleados.")
                    if total > 0:
                        emp = data["empleados"][0]
                        print(f"   Primer empleado: {emp['nombre_completo']} ({emp['punto_trabajo']})")

    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_remote_mcp())
