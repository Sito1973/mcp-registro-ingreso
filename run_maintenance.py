import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def run_maintenance():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print("Invocando herramienta de mantenimiento...")
                # La herramienta no requiere argumentos
                result = await session.call_tool("mantenimiento_limpiar_puntos", {})
                data = json.loads(result.content[0].text)
                
                print(f"Resumen: {data.get('mensaje')}")
                print(f"Detalle: {data.get('detalle')}")

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_maintenance())
