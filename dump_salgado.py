import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def dump_salgado():
    url = "https://cocson-mcp-registro-e-s.6jy9qo.easypanel.host/sse"
    
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Search for Salgado
                res = await session.call_tool("buscar_empleado", {"termino": "SALGADO"})
                search = json.loads(res.content[0].text)
                emp = search["empleados"][0]
                emp_id = emp["id"]
                
                print(f"DEBUG: Empleado ID: {emp_id}")
                print(f"DEBUG: Empleado Raw Data: {json.dumps(emp, indent=2)}")
                
                # Check 2025-12-02 records
                res_reg = await session.call_tool("consultar_registros_fecha", {"fecha": "2025-12-02", "empleado_id": emp_id})
                regs = json.loads(res_reg.content[0].text)
                print(f"\nDEBUG: Registros 2025-12-02 Raw Data: {json.dumps(regs, indent=2)}")
                
                # Check calculate hours
                res_hrs = await session.call_tool("calcular_horas_trabajadas_dia", {"fecha": "2025-12-02", "empleado_id": emp_id})
                hrs = json.loads(res_hrs.content[0].text)
                print(f"\nDEBUG: Calcular Horas 2025-12-02 Raw Data: {json.dumps(hrs, indent=2)}")

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(dump_salgado())
