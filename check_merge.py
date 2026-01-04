import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def check_records():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    id_to_delete = "90f904b3-390c-4625-87b3-34b8a4913034"
    id_to_keep = "a8159e76-1995-40c4-98f2-4cba0fcf46b5"
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # We don't have a "count_registros" tool but we can use estadisticas_asistencia 
                # for a wide range or just try to fetch a few records.
                # Actually, I'll add a temporary "maintenance_check_merge" tool.
                
                print("Invocando auditoría de registros para Alexis...")
                # For now I will use a simple query tool if available or add a new one.
                # I'll add a discovery tool to the server again.
                pass

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_records())
