import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def list_puntos():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Use estadisticas_asistencia to see points
                print("Consultando estadisticas para ver puntos...")
                res = await session.call_tool(
                    "estadisticas_asistencia",
                    {"fecha_inicio": "2025-12-01", "fecha_fin": "2026-01-05"}
                )
                data = json.loads(res.content[0].text)
                print(f"Puntos encontrados:\n{json.dumps(data['por_restaurante'], indent=2)}")

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(list_puntos())
