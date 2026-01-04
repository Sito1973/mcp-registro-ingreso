import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def count_alexis():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    
    id1 = "90f904b3-390c-4625-87b3-34b8a4913034" # Código 1268237
    id2 = "a8159e76-1995-40c4-98f2-4cba0fcf46b5" # Código Alexis
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                print("Contando registros para Alexis...")
                
                # Usamos consultar_registros_rango para ver si hay algo
                # Un rango amplio para no dejar dudas
                f_inicio = "2024-01-01"
                f_fin = "2026-12-31"
                
                print(f"\nConsultando ID 1268237 ({id1})...")
                res1 = await session.call_tool("consultar_registros_rango", {
                    "fecha_inicio": f_inicio,
                    "fecha_fin": f_fin,
                    "empleado_id": id1
                })
                data1 = json.loads(res1.content[0].text)
                print(f"Total registros: {data1.get('total_registros', 0)}")
                
                print(f"\nConsultando ID Alexis ({id2})...")
                res2 = await session.call_tool("consultar_registros_rango", {
                    "fecha_inicio": f_inicio,
                    "fecha_fin": f_fin,
                    "empleado_id": id2
                })
                data2 = json.loads(res2.content[0].text)
                print(f"Total registros: {data2.get('total_registros', 0)}")

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(count_alexis())
