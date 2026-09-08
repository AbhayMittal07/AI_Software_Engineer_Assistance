# login_test.py
import asyncio
from app.db.session import SessionLocal
from app.services.auth_service import AuthService

async def main():
    async with SessionLocal() as session:
        svc = AuthService(session)
        try:
            resp = await svc.login("demo@example.com", "Demo@12345")
            print("LOGIN_OK", resp.tokens.access_token)
        except Exception as e:
            print("LOGIN_FAIL", type(e).__name__, str(e))

if __name__ == "__main__":
    asyncio.run(main())
