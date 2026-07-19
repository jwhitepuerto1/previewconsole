"""
GET/POST/PATCH/DELETE /api/data-room, /{id}/access-log, /{id}/grant-access/{target_id}.

client_readonly gets "read:data_room_approved" (a distinct, narrower
permission from client_admin/team's "read:data_room") — per section 5's
role table ("Client Read-Only | investors, observers | View only — portal,
data room (gated), reports"), so list_documents filters to access_level ==
"public" for that permission specifically rather than exposing every
document.

The schema (section 7) has no per-investor-per-document grants table —
data_room_access_log records *views*, not grants. grant-access is
implemented as inserting a log row marking the grant itself (accessed_by
"system:grant", no duration), so it's visible in that document's access
history; it doesn't change what a client_readonly investor's own list_documents
call returns (still gated purely by access_level), since there's no schema
support for per-investor document visibility beyond that one tier.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.permissions import has_permission
from app.db.models.client_raise import DataRoomAccessLog, DataRoomDocument
from app.db.session import get_tenant_db
from app.services.alert_dispatcher import create_alert

router = APIRouter()

_FULL_READ_PERMS = ("read:data_room", "read:all_assigned_clients", "*")
_GATED_READ_PERMS = ("read:data_room_approved",)
_WRITE_PERMS = ("write:data_room", "*")


class DocumentOut(BaseModel):
    id: uuid.UUID
    document_name: str | None
    document_type: str | None
    file_path: str | None
    file_size_bytes: int | None
    version: int
    access_level: str | None
    uploaded_by: str | None
    uploaded_at: datetime


class UploadDocumentRequest(BaseModel):
    document_name: str
    document_type: str
    file_path: str
    file_size_bytes: int | None = None
    access_level: str = "qualified"
    uploaded_by: str | None = None


class UpdateDocumentRequest(BaseModel):
    document_name: str | None = None
    access_level: str | None = None
    is_active: bool | None = None


def _to_out(d: DataRoomDocument) -> DocumentOut:
    return DocumentOut(
        id=d.id, document_name=d.document_name, document_type=d.document_type,
        file_path=d.file_path, file_size_bytes=d.file_size_bytes, version=d.version,
        access_level=d.access_level, uploaded_by=d.uploaded_by, uploaded_at=d.uploaded_at,
    )


def _require_data_room_read(request: Request) -> None:
    role = request.state.role
    if not role or not (any(has_permission(role, p) for p in _FULL_READ_PERMS) or any(has_permission(role, p) for p in _GATED_READ_PERMS)):
        raise HTTPException(status_code=403, detail="Role lacks any data-room read permission.")


@router.get("", response_model=list[DocumentOut], dependencies=[Depends(_require_data_room_read)])
async def list_documents(request: Request, db: AsyncSession = Depends(get_tenant_db)):
    role = request.state.role
    query = select(DataRoomDocument).where(DataRoomDocument.is_active.is_(True))
    if not any(has_permission(role, p) for p in _FULL_READ_PERMS):
        query = query.where(DataRoomDocument.access_level == "public")
    rows = (await db.execute(query.order_by(DataRoomDocument.uploaded_at.desc()))).scalars().all()
    return [_to_out(d) for d in rows]


@router.post("", response_model=DocumentOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def upload_document(body: UploadDocumentRequest, db: AsyncSession = Depends(get_tenant_db)):
    document = DataRoomDocument(
        document_name=body.document_name, document_type=body.document_type, file_path=body.file_path,
        file_size_bytes=body.file_size_bytes, access_level=body.access_level, uploaded_by=body.uploaded_by,
    )
    db.add(document)
    await db.commit()
    return _to_out(document)


@router.patch("/{document_id}", response_model=DocumentOut, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def update_document(document_id: uuid.UUID, body: UpdateDocumentRequest, db: AsyncSession = Depends(get_tenant_db)):
    document = await db.get(DataRoomDocument, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    await db.commit()
    return _to_out(document)


@router.delete("/{document_id}", status_code=204, dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def delete_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    document = await db.get(DataRoomDocument, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    document.is_active = False
    await db.commit()


@router.get("/{document_id}/access-log", dependencies=[Depends(require_permission(*_FULL_READ_PERMS))])
async def access_log(document_id: uuid.UUID, db: AsyncSession = Depends(get_tenant_db)):
    rows = (
        await db.execute(
            select(DataRoomAccessLog).where(DataRoomAccessLog.document_id == document_id).order_by(DataRoomAccessLog.accessed_at.desc())
        )
    ).scalars().all()
    return {
        "access_log": [
            {
                "investor_target_id": str(a.investor_target_id) if a.investor_target_id else None,
                "accessed_by": a.accessed_by, "accessed_at": a.accessed_at.isoformat(),
                "access_duration_seconds": a.access_duration_seconds,
            }
            for a in rows
        ]
    }


@router.post("/{document_id}/grant-access/{target_id}", dependencies=[Depends(require_permission(*_WRITE_PERMS))])
async def grant_access(document_id: uuid.UUID, target_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_tenant_db)):
    document = await db.get(DataRoomDocument, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    claims = request.state.claims or {}
    db.add(DataRoomAccessLog(
        document_id=document_id, investor_target_id=target_id,
        accessed_by=f"grant:{claims.get('email', 'unknown')}",
    ))
    await db.commit()

    if request.state.client_id:
        await create_alert(
            db, request.state.client_id,
            alert_type="document_accessed", severity="info",
            title="Data room access granted",
            message=f"Access granted to {document.document_name}",
            related_investor_id=target_id,
        )

    return {"status": "granted"}
