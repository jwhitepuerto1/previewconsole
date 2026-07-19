"""GET /api/notes/{target_id}, POST/PATCH/DELETE /api/notes."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.models.client_raise import InvestorNote
from app.db.session import get_tenant_db

router = APIRouter()

_READ_PERMS = ("read:own_raise", "read:all_assigned_clients", "*")
_WRITE_PERMS = ("write:notes", "write:pipeline", "*")  # client roles log notes via write:pipeline; reps via write:notes


class NoteOut(BaseModel):
    id: uuid.UUID
    investor_target_id: uuid.UUID | None
    note_type: str | None
    note: str | None
    logged_by: str | None
    logged_at: datetime


class CreateNoteRequest(BaseModel):
    investor_target_id: uuid.UUID
    note_type: str = "general"
    note: str
    logged_by: str | None = None


class UpdateNoteRequest(BaseModel):
    note: str


def _to_out(n: InvestorNote) -> NoteOut:
    return NoteOut(
        id=n.id, investor_target_id=n.investor_target_id, note_type=n.note_type,
        note=n.note, logged_by=n.logged_by, logged_at=n.logged_at,
    )


@router.get("/{target_id}", response_model=list[NoteOut], dependencies=[Depends(require_permission(*_READ_PERMS))])
async def list_notes(target_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    rows = (
        await db.execute(
            select(InvestorNote).where(InvestorNote.investor_target_id == target_id).order_by(InvestorNote.logged_at)
        )
    ).scalars().all()
    return [_to_out(n) for n in rows]


@router.post("", response_model=NoteOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def create_note(body: CreateNoteRequest, db: AsyncSession = Depends(get_tenant_db)):
    note = InvestorNote(
        investor_target_id=body.investor_target_id, note_type=body.note_type,
        note=body.note, logged_by=body.logged_by,
    )
    db.add(note)
    await db.commit()
    return _to_out(note)


@router.patch("/{note_id}", response_model=NoteOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def update_note(note_id: uuid.UUID, body: UpdateNoteRequest, db: AsyncSession = Depends(get_tenant_db)):
    note = await db.get(InvestorNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    note.note = body.note
    await db.commit()
    return _to_out(note)


@router.delete("/{note_id}", status_code=204, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def delete_note(note_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    note = await db.get(InvestorNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    await db.delete(note)
    await db.commit()
    return Response(status_code=204)
