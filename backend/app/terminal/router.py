"""
Browser-based PTY terminal over WebSocket.

Each connection spawns a real bash process in the user's session workspace.
Git is pre-configured with the user's stored GitHub OAuth token so
`git push` works out of the box.

Auth:   JWT as ?token=JWT query param
Input:  {"type": "input",  "data": "<keystrokes>"}
        {"type": "resize", "cols": 80, "rows": 24}
        {"type": "sync",   "files": {"path": "content", ...}}
Output: {"type": "output", "data": "<terminal text>"}
        {"type": "ready",  "github_login": "...", "git_configured": true}
        {"type": "error",  "message": "..."}
"""
import asyncio
import json
import logging
import os
import struct
import sys
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError

from app import db
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["terminal"])

_PTY_OK = sys.platform != "win32"
if _PTY_OK:
    import fcntl
    import termios

_WS_CLOSE_AUTH = 4001
_WS_CLOSE_FORBIDDEN = 4003
_WORKSPACE_ROOT = Path("/tmp/proofforge_terminal")


# ── helpers ────────────────────────────────────────────────────────────────────

def _workspace_dir(session_id: str) -> Path:
    p = _WORKSPACE_ROOT / "ws" / session_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _home_dir(user_id: str) -> Path:
    p = _WORKSPACE_ROOT / "homes" / user_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_files(directory: Path, files: dict) -> None:
    for rel_path, content in files.items():
        # Prevent directory traversal
        parts = [p for p in Path(rel_path).parts if p not in ("", "..", ".")]
        if not parts:
            continue
        target = directory / Path(*parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _configure_git(home: Path, user: dict) -> None:
    name = (user.get("name") or user.get("github_login") or "User").replace('"', '')
    login = user.get("github_login") or "user"
    email = user.get("email") or f"{login}@users.noreply.github.com"
    token = user.get("github_access_token")

    (home / ".gitconfig").write_text(
        f'[user]\n\tname = {name}\n\temail = {email}\n'
        '[credential]\n\thelper = store\n'
        '[init]\n\tdefaultBranch = main\n'
        '[core]\n\tautocrlf = input\n',
        encoding="utf-8",
    )

    if token:
        creds = home / ".git-credentials"
        creds.write_text(f"https://x-access-token:{token}@github.com\n", encoding="utf-8")
        creds.chmod(0o600)


# ── WebSocket endpoint ─────────────────────────────────────────────────────────

@router.websocket("/ws/terminal/{session_id}")
async def terminal_ws(websocket: WebSocket, session_id: str) -> None:
    if not _PTY_OK:
        await websocket.accept()
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Terminal requires Linux (not available in dev mode on Windows)",
        }))
        await websocket.close()
        return

    # ── Auth ──────────────────────────────────────────────────────────────────
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=_WS_CLOSE_AUTH)
        return
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub") or ""
        if not user_id:
            raise JWTError("no sub")
    except JWTError:
        await websocket.close(code=_WS_CLOSE_AUTH)
        return

    await websocket.accept()

    # ── Session ownership ─────────────────────────────────────────────────────
    session = await db.fetchrow(
        "SELECT user_id FROM active_sessions WHERE id=$1::uuid", session_id
    )
    if not session or str(session["user_id"]) != user_id:
        await websocket.send_text(json.dumps({
            "type": "error", "message": "Session not found or unauthorized",
        }))
        await websocket.close(code=_WS_CLOSE_FORBIDDEN)
        return

    user = await db.fetchrow(
        "SELECT id, github_login, name, email, github_access_token "
        "FROM users WHERE id=$1::uuid",
        user_id,
    )
    if not user:
        await websocket.close(code=_WS_CLOSE_AUTH)
        return

    user_dict = dict(user)
    home = _home_dir(user_id)
    workspace = _workspace_dir(session_id)
    _configure_git(home, user_dict)

    # ── Wait for initial file sync (10 s) ─────────────────────────────────────
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        msg = json.loads(raw)
        if msg.get("type") == "sync" and isinstance(msg.get("files"), dict):
            _write_files(workspace, msg["files"])
    except (asyncio.TimeoutError, json.JSONDecodeError, KeyError):
        pass  # start shell anyway — user may sync later

    # ── Shell environment ─────────────────────────────────────────────────────
    login = user_dict.get("github_login") or "user"
    env = {
        "HOME": str(home),
        "USER": login,
        "LOGNAME": login,
        "SHELL": "/bin/bash",
        "TERM": "xterm-256color",
        "COLORTERM": "truecolor",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "HISTFILE": str(home / ".bash_history"),
    }

    await websocket.send_text(json.dumps({
        "type": "ready",
        "github_login": login,
        "git_configured": bool(user_dict.get("github_access_token")),
        "cwd": str(workspace),
    }))

    # ── Spawn PTY ─────────────────────────────────────────────────────────────
    master_fd, slave_fd = os.openpty()
    proc = None
    loop = asyncio.get_running_loop()

    try:
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))

        proc = await asyncio.create_subprocess_exec(
            "/bin/bash",
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            cwd=str(workspace),
            preexec_fn=os.setsid,
        )
        os.close(slave_fd)
        slave_fd = -1

        # Queue PTY output → WebSocket
        out_q: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=512)

        def _on_pty_readable() -> None:
            try:
                chunk = os.read(master_fd, 4096)
                out_q.put_nowait(chunk)
            except (OSError, BlockingIOError):
                out_q.put_nowait(None)
                try:
                    loop.remove_reader(master_fd)
                except Exception:
                    pass

        loop.add_reader(master_fd, _on_pty_readable)

        async def _send_loop() -> None:
            while True:
                chunk = await out_q.get()
                if chunk is None:
                    break
                try:
                    await websocket.send_text(json.dumps({
                        "type": "output",
                        "data": chunk.decode("utf-8", errors="replace"),
                    }))
                except Exception:
                    break

        async def _recv_loop() -> None:
            while True:
                try:
                    raw = await websocket.receive_text()
                    msg = json.loads(raw)
                    t = msg.get("type")
                    if t == "input":
                        data = msg.get("data", "")
                        if data:
                            os.write(master_fd, data.encode("utf-8"))
                    elif t == "resize":
                        cols = max(1, int(msg.get("cols", 80)))
                        rows = max(1, int(msg.get("rows", 24)))
                        fcntl.ioctl(
                            master_fd, termios.TIOCSWINSZ,
                            struct.pack("HHHH", rows, cols, 0, 0),
                        )
                    elif t == "sync" and isinstance(msg.get("files"), dict):
                        _write_files(workspace, msg["files"])
                except WebSocketDisconnect:
                    break
                except (json.JSONDecodeError, KeyError, OSError):
                    pass
                except Exception as exc:
                    logger.debug("terminal recv: %s", exc)
                    break

        send_task = asyncio.create_task(_send_loop())
        recv_task = asyncio.create_task(_recv_loop())

        _done, pending = await asyncio.wait(
            [send_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()

    except Exception as exc:
        logger.warning("Terminal session %s: %s", session_id, exc)
    finally:
        try:
            loop.remove_reader(master_fd)
        except Exception:
            pass
        try:
            os.close(master_fd)
        except Exception:
            pass
        if slave_fd != -1:
            try:
                os.close(slave_fd)
            except Exception:
                pass
        if proc is not None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=3.0)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        try:
            await websocket.close()
        except Exception:
            pass
