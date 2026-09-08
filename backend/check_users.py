# check_users.py
import asyncio
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.user import User

async def main():
    async with SessionLocal() as session:
        res = await session.execute(select(User))
        users = res.scalars().all()
        if not users:
            print("NO_USERS")
        for u in users:
            print(u.id, u.email, u.is_active, getattr(u, "hashed_password", "<no-hash>"))

if __name__ == "__main__":
    asyncio.run(main())
