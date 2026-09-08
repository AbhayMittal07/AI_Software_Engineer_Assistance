import asyncio
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.repository import Repository
from sqlalchemy import select

print('DB_URL', settings.DATABASE_URL)

async def main():
    async with SessionLocal() as session:
        result = await session.execute(select(Repository))
        rows = result.scalars().all()
        print('REPOS', [(r.id, r.name, r.status.value, r.user_id) for r in rows])

asyncio.run(main())
