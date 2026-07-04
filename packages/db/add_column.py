import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

async def run():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set")
        return
        
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    db_url = db_url.replace("?sslmode=require", "?ssl=require")
    db_url = db_url.replace("&sslmode=require", "&ssl=require")
    db_url = db_url.replace("?channel_binding=require", "")
    db_url = db_url.replace("&channel_binding=require", "")
    if db_url.endswith("?"): db_url = db_url[:-1]
    
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)")
        print("Successfully added password_hash column.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run())
