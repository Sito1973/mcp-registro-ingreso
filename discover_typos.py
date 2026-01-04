import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def discover_typos():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print("Invocando herramienta de descubrimiento de typos...")
                result = await session.call_tool("maintenance_buscar_typos", {})
                data = json.loads(result.content[0].text)
                
                print(f"RESULTADOS: {json.dumps(data.get('resultados'), indent=2)}")
                print(f"MENSAJE: {data.get('mensaje')}")

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(discover_typos())
