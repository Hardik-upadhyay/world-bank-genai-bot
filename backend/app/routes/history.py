"""
Chat History Routes – JWT-authenticated endpoints for saving / retrieving
per-user chat sessions and messages from SQLite.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.auth.auth_service import decode_access_token, CurrentUser
from app.db.database import get_connection
from app.db.queries import get_user_by_id

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


# ── Auth helper ────────────────────────────────────────────────────────────────

def _resolve_user(creds: Optional[HTTPAuthorizationCredentials]) -> Optional[CurrentUser]:
    """Return CurrentUser from JWT or None if missing/invalid."""
    if not creds:
        return None
    payload = decode_access_token(creds.credentials)
    if not payload:
        return None
    user_id = int(payload.get("sub", 0))
    user_row = get_user_by_id(user_id)
    if not user_row:
        return None
    return CurrentUser(
        user_id=user_id,
        role=payload.get("role", ""),
        full_name=payload.get("full_name", ""),
        username=user_row["username"],
    )


# ── Pydantic request/response models ──────────────────────────────────────────

class MessageIn(BaseModel):
    role: str               # 'user' | 'assistant'
    content: str
    model_used: Optional[str] = None


class CreateSessionRequest(BaseModel):
    title: str = "New Conversation"
    messages: list[MessageIn] = []


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    messages: list[MessageIn] = []  # messages to APPEND


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/sessions", status_code=201)
def create_session(
    body: CreateSessionRequest,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Create a new chat session (called on first user message)."""
    user = _resolve_user(creds)
    if not user:
        return {"error": "Unauthorized"}

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)",
            (user.user_id, body.title[:120]),
        )
        session_id = cur.lastrowid
        for msg in body.messages:
            cur.execute(
                "INSERT INTO chat_messages (session_id, role, content, model_used) VALUES (?, ?, ?, ?)",
                (session_id, msg.role, msg.content, msg.model_used),
            )
        conn.commit()
        return {"session_id": session_id}
    finally:
        conn.close()


@router.put("/sessions/{session_id}")
def update_session(
    session_id: int,
    body: UpdateSessionRequest,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Append messages + optionally update title. Verifies ownership."""
    user = _resolve_user(creds)
    if not user:
        return {"error": "Unauthorized"}

    conn = get_connection()
    try:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user.user_id),
        ).fetchone()
        if not row:
            return {"error": "Session not found"}

        if body.title:
            cur.execute(
                "UPDATE chat_sessions SET title = ?, updated_at = datetime('now') WHERE id = ?",
                (body.title[:120], session_id),
            )
        else:
            cur.execute(
                "UPDATE chat_sessions SET updated_at = datetime('now') WHERE id = ?",
                (session_id,),
            )

        for msg in body.messages:
            cur.execute(
                "INSERT INTO chat_messages (session_id, role, content, model_used) VALUES (?, ?, ?, ?)",
                (session_id, msg.role, msg.content, msg.model_used),
            )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.get("/sessions")
def list_sessions(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Return all sessions for the current user (newest first, no messages)."""
    user = _resolve_user(creds)
    if not user:
        return {"error": "Unauthorized"}

    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, title, created_at, updated_at
               FROM chat_sessions
               WHERE user_id = ?
               ORDER BY updated_at DESC
               LIMIT 50""",
            (user.user_id,),
        ).fetchall()
        return {"sessions": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Return a single session with all its messages."""
    user = _resolve_user(creds)
    if not user:
        return {"error": "Unauthorized"}

    conn = get_connection()
    try:
        session = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user.user_id),
        ).fetchone()
        if not session:
            return {"error": "Session not found"}

        messages = conn.execute(
            "SELECT role, content, model_used, created_at FROM chat_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()

        return {
            "session": dict(session),
            "messages": [dict(m) for m in messages],
        }
    finally:
        conn.close()


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Delete a session and all its messages."""
    user = _resolve_user(creds)
    if not user:
        return {"error": "Unauthorized"}

    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user.user_id),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()
