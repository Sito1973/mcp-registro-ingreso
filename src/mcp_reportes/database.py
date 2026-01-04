"""Módulo de conexión a base de datos PostgreSQL async"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()


class Database:
    """Clase para manejar conexiones async a PostgreSQL"""
    
    def __init__(self):
        # Buscar en múltiples variables de entorno
        self.database_url = (
            os.getenv("DATABASE_URL_ASYNC") or
            os.getenv("DATABASE_URL_FALLBACK") or
            "postgresql+asyncpg://cocson:password@localhost:5432/acceso-cocson"
        )
        self.engine = None
        self.session_factory = None

    async def connect(self):
        """Establece conexión con la base de datos"""
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_size=5,
            max_overflow=10
        )
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def disconnect(self):
        """Cierra la conexión"""
        if self.engine:
            await self.engine.dispose()

    async def execute(self, query: str, params: dict = None) -> list[dict]:
        """Ejecuta una consulta y retorna resultados como lista de dicts"""
        async with self.session_factory() as session:
            result = await session.execute(text(query), params or {})
            rows = result.fetchall()
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]

    async def execute_one(self, query: str, params: dict = None) -> dict | None:
        """Ejecuta una consulta y retorna un solo resultado"""
        results = await self.execute(query, params)
        return results[0] if results else None
