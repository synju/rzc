import asyncio
from sqlalchemy import text
from database import engine


async def migrate():
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'admin_wallet'
        """))
        table_exists = result.fetchone()
        
        if not table_exists:
            print("Creating admin_wallet table...")
            await conn.execute(text("""
                CREATE TABLE admin_wallet (
                    id VARCHAR(36) PRIMARY KEY,
                    address VARCHAR(42) UNIQUE NOT NULL,
                    encrypted_private_key TEXT NOT NULL,
                    avax_balance BIGINT DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("Created admin_wallet table")
        else:
            print("admin_wallet table already exists")
        
        print("Migration completed!")


if __name__ == "__main__":
    asyncio.run(migrate())
