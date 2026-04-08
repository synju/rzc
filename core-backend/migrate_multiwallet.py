import asyncio
from sqlalchemy import text
from database import engine


async def migrate():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'wallets'"))
        columns = [row[0] for row in result.fetchall()]
        print(f"Current wallet columns: {columns}")

        if 'name' not in columns:
            print("Adding 'name' column to wallets...")
            await conn.execute(text("ALTER TABLE wallets ADD COLUMN name VARCHAR(255) DEFAULT 'Wallet 1'"))
            print("Added 'name' column")

        if 'is_active' not in columns:
            print("Adding 'is_active' column to wallets...")
            await conn.execute(text("ALTER TABLE wallets ADD COLUMN is_active BOOLEAN DEFAULT FALSE"))
            print("Added 'is_active' column")

        if 'encrypted_wallet_blob' not in columns:
            print("Adding 'encrypted_wallet_blob' column to wallets...")
            await conn.execute(text("ALTER TABLE wallets ADD COLUMN encrypted_wallet_blob TEXT"))
            print("Added 'encrypted_wallet_blob' column")

        result = await conn.execute(text("SELECT id, encrypted_wallet_blob FROM users WHERE encrypted_wallet_blob IS NOT NULL"))
        user_blobs = result.fetchall()
        if user_blobs:
            print(f"Migrating {len(user_blobs)} user wallet blobs to first wallet per user...")
            for user_id, blob in user_blobs:
                wallet_result = await conn.execute(text("SELECT id FROM wallets WHERE user_id = :user_id LIMIT 1"), {"user_id": user_id})
                wallet = wallet_result.fetchone()
                if wallet:
                    await conn.execute(
                        text("UPDATE wallets SET encrypted_wallet_blob = :blob WHERE id = :wallet_id"),
                        {"blob": blob, "wallet_id": wallet[0]}
                    )
                    print(f"  Migrated blob for user {user_id}")

        await conn.execute(text("UPDATE wallets SET is_active = TRUE WHERE (user_id, id) IN (SELECT user_id, MIN(id) FROM wallets GROUP BY user_id HAVING COUNT(*) = 1)"))
        await conn.execute(text("UPDATE wallets SET name = 'Wallet 1' WHERE name IS NULL OR name = ''"))

        print("Migration completed!")


if __name__ == "__main__":
    asyncio.run(migrate())
