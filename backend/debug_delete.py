import asyncio
import os
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///C:/app/var/app.db')
from app.db.session import SessionLocal
from app.repositories.analysis_repository import RepositoryRepository
from app.services.repository_service import RepositoryService

async def main():
    async with SessionLocal() as session:
        repo = await RepositoryRepository(session).get_owned(2, 2, True)
        print('repo', repo.id, repo.name if repo else None)
        if repo is None:
            return
        try:
            await RepositoryService(session).delete(repo)
            print('deleted')
        except Exception as e:
            print(type(e).__name__, e)
            import traceback
            traceback.print_exc()
            raise

asyncio.run(main())
