import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def run_maintenance_debug():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print("Invocando herramienta de mantenimiento (DEBUG)...")
                result = await session.call_tool("mantenimiento_limpiar_puntos", {})
                raw_text = result.content[0].text
                print(f"RAW RESPONSE: {raw_text}")
                
                data = json.loads(raw_text)
                print(f"PARSED DATA: {data}")

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_maintenance_debug())
