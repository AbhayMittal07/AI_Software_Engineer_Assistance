import asyncio
from app.db.session import SessionLocal
from app.repositories.analysis_repository import RepositoryRepository
from app.services.repository_service import RepositoryService

async def main():
    async with SessionLocal() as session:
        repo = await RepositoryRepository(session).get_owned(2, 2, True)
        print('repo2', repo.name if repo else None)
        if repo:
            await RepositoryService(session).delete(repo)
            print('deleted 2')
        repo3 = await RepositoryRepository(session).get_owned(3, 2, True)
        print('repo3', repo3.name if repo3 else None)
        if repo3:
            await RepositoryService(session).delete(repo3)
            print('deleted 3')

asyncio.run(main())
