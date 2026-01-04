import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def find_alexis():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print("Buscando a Alexis...")
                result = await session.call_tool("buscar_empleado", {"termino": "alexis"})
                data = json.loads(result.content[0].text)
                
                if data["resultados"] == 0:
                    print("No se encontró a ningún empleado llamado Alexis.")
                    return
                
                print(f"Resultados encontrados: {data['resultados']}")
                for emp in data["empleados"]:
                    print(f"- Nombre: {emp['nombre_completo']}")
                    print(f"  ID: {emp['id']}")
                    print(f"  Código: {emp['codigo_empleado']}")
                    print(f"  Cargo: {emp['cargo']}")
                    print("-" * 20)

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(find_alexis())
