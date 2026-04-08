import asyncio
from sqlalchemy import text
from database import engine


async def migrate():
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'wallets' AND column_name = 'last_synced_block'
        """))
        column_exists = result.fetchone()
        
        if not column_exists:
            print("Adding 'last_synced_block' column to wallets...")
            await conn.execute(text(
                "ALTER TABLE wallets ADD COLUMN last_synced_block BIGINT"
            ))
            print("Added 'last_synced_block' column")
        else:
            print("Column 'last_synced_block' already exists")
        
        print("Migration completed!")


if __name__ == "__main__":
    asyncio.run(migrate())
