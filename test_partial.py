import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def test_partial_match():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                emp_id = "bf3da283-f546-455c-8d23-ea5b8075b317" # Salgado
                
                # Query with "Leños" (Partial)
                filter_name = "Leños"
                print(f"Consultando registros con filtro PARCIAL: '{filter_name}'...")
                res = await session.call_tool(
                    "consultar_registros_fecha",
                    {"fecha": "2025-12-02", "empleado_id": emp_id, "restaurante": filter_name}
                )
                data = json.loads(res.content[0].text)
                print(f"Resultados con '{filter_name}': {data['total_registros']}")

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_partial_match())
