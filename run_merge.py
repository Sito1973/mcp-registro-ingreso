import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def run_merge():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    
    id_orig = "90f904b3-390c-4625-87b3-34b8a4913034"
    id_dest = "a8159e76-1995-40c4-98f2-4cba0fcf46b5"
    nuevo_cod = "1268237"
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print(f"Fusionando Alexis...")
                print(f"Origen: {id_orig}")
                print(f"Destino: {id_dest}")
                print(f"Nuevo Código: {nuevo_cod}")
                
                result = await session.call_tool("maintenance_fusionar_empleados", {
                    "id_origen": id_orig,
                    "id_destino": id_dest,
                    "nuevo_codigo": nuevo_cod
                })
                
                data = json.loads(result.content[0].text)
                print(f"\nRESULTADO: {json.dumps(data, indent=2, ensure_ascii=False)}")

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_merge())
