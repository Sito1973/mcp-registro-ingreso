import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

async def cleanup_puntos():
    database_url = (
        os.getenv("DATABASE_URL_ASYNC") or
        os.getenv("DATABASE_URL_FALLBACK")
    )
    
    if not database_url:
        print("Error: No se encontró DATABASE_URL_ASYNC o DATABASE_URL_FALLBACK")
        return

    print(f"Conectando a la base de datos...")
    engine = create_async_engine(database_url)
    
    try:
        async with engine.begin() as conn:
            # 1. Ver cuántos registros hay con el typo
            check_query = text("SELECT COUNT(*) FROM registros WHERE punto_trabajo ILIKE '%Leños%Parrila%'")
            result = await conn.execute(check_query)
            count = result.scalar()
            print(f"Encontrados {count} registros con el nombre incorrecto ('Leños Y Parrila').")
            
            if count > 0:
                # 2. Ejecutar el update
                print("Actualizando registros a 'Leños y Parrilla'...")
                update_query = text("""
                    UPDATE registros 
                    SET punto_trabajo = 'Leños y Parrilla' 
                    WHERE punto_trabajo ILIKE '%Leños%Parrila%'
                """)
                update_res = await conn.execute(update_query)
                print(f"✅ Se actualizaron {update_res.rowcount} registros exitosamente.")
            else:
                print("No se requiere actualización.")

    except Exception as e:
        print(f"❌ ERROR durante la limpieza: {str(e)}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(cleanup_puntos())
