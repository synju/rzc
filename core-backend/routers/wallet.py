import traceback
from eth_account import Account
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, User, Wallet
from routers.auth import get_current_user

ERROR_LOG = "error.log"


def log_error(msg: str):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{msg}\n")
        f.write(traceback.format_exc())
        f.write("\n")


router = APIRouter(prefix="/wallet", tags=["wallet"])


class WalletResponse(BaseModel):
    id: str
    name: str
    address: str | None
    balance: int
    is_active: bool


class WalletListResponse(BaseModel):
    wallets: list[WalletResponse]
    active_wallet: WalletResponse | None


class CreateWalletResponse(BaseModel):
    id: str
    name: str
    address: str
    encrypted_private_key: str


class CreateWalletRequest(BaseModel):
    name: str = "Wallet 1"


def encrypt_private_key(private_key: str, encryption_key: str) -> str:
    from cryptography.fernet import Fernet
    import base64
    key = base64.urlsafe_b64encode(encryption_key.encode().ljust(32)[:32])
    f = Fernet(key)
    return f.encrypt(private_key.encode()).decode()


def decrypt_private_key(encrypted_key: str, encryption_key: str) -> str:
    from cryptography.fernet import Fernet
    import base64
    key = base64.urlsafe_b64encode(encryption_key.encode().ljust(32)[:32])
    f = Fernet(key)
    return f.decrypt(encrypted_key.encode()).decode()


@router.get("/", response_model=WalletListResponse)
async def get_wallets(current_user: User = Depends(get_current_user)):
    async with AsyncSession(engine) as db:
        result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
        wallets = result.scalars().all()

        wallet_responses = [
            WalletResponse(
                id=w.id,
                name=w.name,
                address=w.address,
                balance=w.balance,
                is_active=w.is_active
            )
            for w in wallets
        ]

        active_wallet = next((w for w in wallet_responses if w.is_active), None)

        return WalletListResponse(wallets=wallet_responses, active_wallet=active_wallet)


@router.post("/create", response_model=CreateWalletResponse)
async def create_wallet(request: CreateWalletRequest, current_user: User = Depends(get_current_user)):
    async with AsyncSession(engine) as db:
        acct = Account.create()
        encrypted_pk = encrypt_private_key(acct.key.hex(), current_user.id)

        result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
        existing_wallets = result.scalars().all()

        is_first = len(existing_wallets) == 0

        wallet = Wallet(
            user_id=current_user.id,
            name=request.name,
            address=acct.address,
            balance=0,
            is_active=is_first,
            encrypted_wallet_blob=encrypted_pk
        )
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)

        return CreateWalletResponse(
            id=wallet.id,
            name=wallet.name,
            address=wallet.address,
            encrypted_private_key=encrypted_pk
        )


@router.post("/switch/{wallet_id}")
async def switch_wallet(wallet_id: str, current_user: User = Depends(get_current_user)):
    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(select(Wallet).where(Wallet.id == wallet_id, Wallet.user_id == current_user.id))
            wallet = result.scalar_one_or_none()

            if wallet is None:
                raise HTTPException(status_code=404, detail="Wallet not found")

            await db.execute(
                update(Wallet)
                .where(Wallet.user_id == current_user.id)
                .values(is_active=False)
            )

            await db.execute(
                update(Wallet)
                .where(Wallet.id == wallet_id)
                .values(is_active=True)
            )
            await db.commit()

            return {"message": "Wallet switched successfully", "wallet_id": wallet_id}
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Wallet] switch_wallet error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balance")
async def get_balance(current_user: User = Depends(get_current_user)):
    async with AsyncSession(engine) as db:
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == current_user.id, Wallet.is_active == True)
        )
        wallet = result.scalar_one_or_none()

        if wallet is None or not wallet.address:
            return {"address": None, "balance": 0, "synced": False}

        return {
            "address": wallet.address,
            "balance": wallet.balance,
            "synced": True
        }


@router.post("/sync-balance")
async def sync_balance(current_user: User = Depends(get_current_user)):
    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(
                select(Wallet).where(Wallet.user_id == current_user.id, Wallet.is_active == True)
            )
            wallet = result.scalar_one_or_none()

            if wallet is None or not wallet.address:
                raise HTTPException(status_code=404, detail="Wallet not found")

            wallet_id = wallet.id
            wallet_address = wallet.address

            contract_address = "0x8583645670154b3bc3f9c48a1864261fd1f26758"
            rpc_url = "https://avalanche-c-chain-rpc.publicnode.com"

            selector = "0x70a08231"
            address_hex = wallet_address[2:].lower().zfill(64)
            data = selector + address_hex

            from httpx import AsyncClient
            async with AsyncClient() as client:
                response = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [{"to": contract_address, "data": data}, "latest"],
                    "id": 1
                })

            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch balance from blockchain")

            result_data = response.json()

            if "error" in result_data:
                raise HTTPException(status_code=500, detail=f"RPC error: {result_data['error']}")

            balance_hex = result_data.get("result", "0x0")

            if not balance_hex or len(balance_hex) <= 2:
                balance = 0
            else:
                balance = int(balance_hex, 16)

            await db.execute(
                update(Wallet).where(Wallet.id == wallet_id).values(balance=balance)
            )
            await db.commit()

            return {"address": wallet_address, "balance": balance}
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Wallet] sync_balance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{wallet_id}")
async def rename_wallet(wallet_id: str, request: dict, current_user: User = Depends(get_current_user)):
    name = request.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    
    async with AsyncSession(engine) as db:
        result = await db.execute(select(Wallet).where(Wallet.id == wallet_id, Wallet.user_id == current_user.id))
        wallet = result.scalar_one_or_none()

        if wallet is None:
            raise HTTPException(status_code=404, detail="Wallet not found")

        wallet.name = name
        await db.commit()

        return {"message": "Wallet renamed successfully", "id": wallet_id, "name": name}


@router.delete("/{wallet_id}")
async def delete_wallet(wallet_id: str, current_user: User = Depends(get_current_user)):
    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(select(Wallet).where(Wallet.id == wallet_id, Wallet.user_id == current_user.id))
            wallet = result.scalar_one_or_none()

            if wallet is None:
                raise HTTPException(status_code=404, detail="Wallet not found")

            was_active = wallet.is_active
            await db.execute(delete(Wallet).where(Wallet.id == wallet_id))

            if was_active:
                remaining_result = await db.execute(
                    select(Wallet).where(Wallet.user_id == current_user.id).limit(1)
                )
                remaining_wallet = remaining_result.scalar_one_or_none()
                if remaining_wallet:
                    await db.execute(
                        update(Wallet).where(Wallet.id == remaining_wallet.id).values(is_active=True)
                    )

            await db.commit()

            return {"message": "Wallet deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Wallet] delete_wallet error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recreate/{wallet_id}", response_model=CreateWalletResponse)
async def recreate_wallet(wallet_id: str, current_user: User = Depends(get_current_user)):
    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(select(Wallet).where(Wallet.id == wallet_id, Wallet.user_id == current_user.id))
            wallet = result.scalar_one_or_none()

            if wallet is None:
                raise HTTPException(status_code=404, detail="Wallet not found")

            wallet_name = wallet.name

            acct = Account.create()
            encrypted_pk = encrypt_private_key(acct.key.hex(), current_user.id)

            await db.execute(
                update(Wallet)
                .where(Wallet.id == wallet_id)
                .values(
                    encrypted_wallet_blob=encrypted_pk,
                    address=acct.address,
                    balance=0
                )
            )
            await db.commit()

            return CreateWalletResponse(
                id=wallet_id,
                name=wallet_name,
                address=acct.address,
                encrypted_private_key=encrypted_pk
            )
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Wallet] recreate_wallet error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
