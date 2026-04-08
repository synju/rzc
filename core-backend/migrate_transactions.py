import asyncio
from sqlalchemy import text
from database import engine


async def migrate():
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'transactions'
        """))
        columns = [row[0] for row in result.fetchall()]
        
        if 'id' not in columns:
            print("Creating transactions table...")
            await conn.execute(text("""
                CREATE TABLE transactions (
                    id VARCHAR(36) PRIMARY KEY,
                    wallet_id VARCHAR(36) NOT NULL,
                    tx_hash VARCHAR(66) UNIQUE NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    from_address VARCHAR(42) NOT NULL,
                    to_address VARCHAR(42) NOT NULL,
                    amount BIGINT NOT NULL,
                    block_number BIGINT,
                    status VARCHAR(20) DEFAULT 'confirmed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (wallet_id) REFERENCES wallets(id)
                )
            """))
            print("Created transactions table")
        else:
            print("Transactions table already exists")
        
        print("Migration completed!")


if __name__ == "__main__":
    asyncio.run(migrate())
