from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, User, Recipient
from routers.auth import get_current_user


router = APIRouter(prefix="/recipients", tags=["recipients"])


class RecipientCreate(BaseModel):
    name: str
    address: str


class RecipientResponse(BaseModel):
    id: str
    name: str
    address: str


@router.get("/", response_model=list[RecipientResponse])
async def get_recipients(current_user: User = Depends(get_current_user)):
    async with AsyncSession(engine) as db:
        result = await db.execute(
            select(Recipient).where(Recipient.user_id == current_user.id)
        )
        recipients = result.scalars().all()
        return [
            RecipientResponse(id=r.id, name=r.name, address=r.address)
            for r in recipients
        ]


@router.post("/", response_model=RecipientResponse)
async def add_recipient(
    request: RecipientCreate,
    current_user: User = Depends(get_current_user)
):
    if len(request.address) != 42 or not request.address.startswith("0x"):
        raise HTTPException(status_code=400, detail="Invalid wallet address")

    async with AsyncSession(engine) as db:
        recipient = Recipient(
            user_id=current_user.id,
            name=request.name,
            address=request.address.lower()
        )
        db.add(recipient)
        await db.commit()
        await db.refresh(recipient)
        return RecipientResponse(
            id=recipient.id,
            name=recipient.name,
            address=recipient.address
        )


@router.delete("/{recipient_id}")
async def remove_recipient(
    recipient_id: str,
    current_user: User = Depends(get_current_user)
):
    async with AsyncSession(engine) as db:
        result = await db.execute(
            select(Recipient).where(
                Recipient.id == recipient_id,
                Recipient.user_id == current_user.id
            )
        )
        recipient = result.scalar_one_or_none()

        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")

        await db.execute(
            delete(Recipient).where(Recipient.id == recipient_id)
        )
        await db.commit()
        return {"message": "Recipient deleted"}