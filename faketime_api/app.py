from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from getpass import getpass
from pathlib import Path
from typing import Any, Iterator

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
DATA_DIR = PROJECT_ROOT / "service_data"
DATABASE_PATH = DATA_DIR / "auth.db"
FAKETIME_PATH = PROJECT_ROOT / "container" / "faketime" / "current.rc"
APP_TEMPLATE_PATH = PACKAGE_DIR / "templates" / "app.html"
SESSION_COOKIE_NAME = "sigesp_session"
SESSION_TTL = timedelta(days=7)
PBKDF2_ITERATIONS = 310_000
LOGGER = logging.getLogger("sigesp.faketime_api")


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_iso8601(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value)


def configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def ensure_storage() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.commit()


@contextmanager
def db_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def encode_password(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return base64.b64encode(digest).decode("ascii")


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_bytes(16)
    return base64.b64encode(salt).decode("ascii"), encode_password(password, salt)


def verify_password(password: str, salt_b64: str, expected_hash: str) -> bool:
    salt = base64.b64decode(salt_b64.encode("ascii"))
    current_hash = encode_password(password, salt)
    return hmac.compare_digest(current_hash, expected_hash)


def normalize_username(raw_username: Any) -> str:
    username = str(raw_username or "").strip().lower()
    if len(username) < 3 or len(username) > 64:
        raise ValueError("username must be between 3 and 64 characters")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    if any(character not in allowed for character in username):
        raise ValueError("username contains unsupported characters")
    return username


def validate_password(password: Any) -> str:
    normalized = str(password or "")
    if len(normalized) < 8:
        raise ValueError("password must be at least 8 characters")
    if len(normalized) > 512:
        raise ValueError("password is too long")
    return normalized


def create_user(username: str, password: str) -> None:
    normalized_username = normalize_username(username)
    normalized_password = validate_password(password)
    salt, password_hash = hash_password(normalized_password)
    created_at = to_iso8601(utc_now())
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO users (username, password_salt, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (normalized_username, salt, password_hash, created_at),
        )


def parse_json(request_data: Any) -> dict[str, Any]:
    if not isinstance(request_data, dict):
        raise ValueError("request body must be a JSON object")
    return request_data


def detect_faketime_mode(value: str) -> str:
    if value.startswith("@") and _is_datetime(value[1:]):
        return "start_at"
    if _is_datetime(value):
        return "absolute"
    if _is_relative(value):
        return "relative"
    return "raw"


def _is_datetime(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False
    return True


def _is_relative(value: str) -> bool:
    import re

    pattern = re.compile(
        r"^[+-]\d+(?:[\.,]\d+)?(?:[mhd y]|y)?(?:\s+[xi]\d+(?:[\.,]\d+)?)?$".replace(
            " ", ""
        )
    )
    return bool(pattern.fullmatch(value))


def normalize_faketime_value(
    raw_value: Any, requested_mode: Any = None
) -> tuple[str, str]:
    value = str(raw_value or "").strip()
    if not value:
        raise ValueError("faketime value is required")
    if any(character in value for character in ("\r", "\n", "\x00")):
        raise ValueError("faketime value cannot contain control characters")

    mode = str(requested_mode or "").strip().lower() or detect_faketime_mode(value)

    if mode == "absolute":
        if not _is_datetime(value):
            raise ValueError("absolute mode expects 'YYYY-MM-DD HH:MM:SS'")
        return value, mode
    if mode == "start_at":
        normalized = value[1:] if value.startswith("@") else value
        if not _is_datetime(normalized):
            raise ValueError(
                "start_at mode expects '@YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD HH:MM:SS'"
            )
        return f"@{normalized}", mode
    if mode == "relative":
        if not _is_relative(value):
            raise ValueError(
                "relative mode expects values like '+14d', '-10m' or '+0 x2'"
            )
        return value, mode
    if mode == "raw":
        return value, mode
    raise ValueError("unsupported faketime mode")


def read_faketime_value() -> dict[str, str]:
    value = FAKETIME_PATH.read_text(encoding="utf-8").strip()
    return {"value": value, "mode": detect_faketime_mode(value)}


def write_faketime_value(value: str) -> None:
    FAKETIME_PATH.write_text(value, encoding="utf-8")


def json_response(data: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status_code)


def error_response(message: str, status_code: int) -> JSONResponse:
    return json_response({"error": message}, status_code=status_code)


def issue_session(user_id: int) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    created_at = utc_now()
    expires_at = created_at + SESSION_TTL
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, to_iso8601(created_at), to_iso8601(expires_at)),
        )
    return token, expires_at


def delete_session(token: str) -> None:
    with db_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))


def fetch_session_user(token: str | None) -> sqlite3.Row | None:
    if not token:
        return None
    with db_connection() as connection:
        session_row = connection.execute(
            "SELECT token, user_id, expires_at FROM sessions WHERE token = ?",
            (token,),
        ).fetchone()
        if session_row is None:
            return None
        if parse_iso8601(session_row["expires_at"]) <= utc_now():
            connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
        return connection.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?",
            (session_row["user_id"],),
        ).fetchone()


def current_user(request: Request) -> sqlite3.Row | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return fetch_session_user(token)


def require_user(request: Request) -> sqlite3.Row:
    user = current_user(request)
    if user is None:
        raise PermissionError("authentication required")
    return user


async def homepage(_: Request) -> JSONResponse:
    return json_response(
        {
            "service": "sigesp faketime api",
            "routes": {
                "health": "GET /health",
                "login": "POST /auth/login",
                "logout": "POST /auth/logout",
                "me": "GET /auth/me",
                "read_faketime": "GET /faketime",
                "write_faketime": "PUT /faketime",
                "terminal_create_user": "uv run faketime-api create-user --username <name>",
            },
            "faketime_modes": {
                "absolute": "YYYY-MM-DD HH:MM:SS",
                "start_at": "@YYYY-MM-DD HH:MM:SS",
                "relative": "+14d, -10m, +0 x2",
                "raw": "Any single-line libfaketime expression",
            },
        }
    )


async def app_page(_: Request) -> HTMLResponse:
    return HTMLResponse(APP_TEMPLATE_PATH.read_text(encoding="utf-8"))


async def health(_: Request) -> JSONResponse:
    return json_response({"status": "ok"})


async def login(request: Request) -> Response:
    try:
        payload = parse_json(await request.json())
        username = normalize_username(payload.get("username"))
        password = validate_password(payload.get("password"))
    except (json.JSONDecodeError, ValueError) as error:
        return error_response(str(error), 400)

    with db_connection() as connection:
        user_row = connection.execute(
            "SELECT id, username, password_salt, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if user_row is None or not verify_password(
        password, user_row["password_salt"], user_row["password_hash"]
    ):
        return error_response("invalid credentials", 401)

    token, expires_at = issue_session(user_row["id"])
    response = json_response(
        {
            "status": "logged_in",
            "username": user_row["username"],
            "expires_at": expires_at.isoformat(),
        }
    )
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=int(SESSION_TTL.total_seconds()),
        secure=False,
    )
    LOGGER.info("logged in user=%s", username)
    return response


async def logout(request: Request) -> Response:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        delete_session(token)

    response = json_response({"status": "logged_out"})
    response.delete_cookie(SESSION_COOKIE_NAME)
    LOGGER.info("logged out session_present=%s", bool(token))
    return response


async def me(request: Request) -> JSONResponse:
    user = current_user(request)
    if user is None:
        return error_response("authentication required", 401)
    return json_response(
        {
            "id": user["id"],
            "username": user["username"],
            "created_at": user["created_at"],
        }
    )


async def get_faketime(request: Request) -> JSONResponse:
    try:
        user = require_user(request)
    except PermissionError as error:
        return error_response(str(error), 401)

    data = read_faketime_value()
    data["updated_by"] = user["username"]
    return json_response(data)


async def set_faketime(request: Request) -> JSONResponse:
    try:
        user = require_user(request)
        payload = parse_json(await request.json())
        normalized_value, mode = normalize_faketime_value(
            payload.get("value"),
            payload.get("mode"),
        )
    except PermissionError as error:
        return error_response(str(error), 401)
    except (json.JSONDecodeError, ValueError) as error:
        return error_response(str(error), 400)

    write_faketime_value(normalized_value)
    LOGGER.info(
        "updated faketime mode=%s user=%s value=%s",
        mode,
        user["username"],
        normalized_value,
    )
    return json_response(
        {
            "status": "updated",
            "mode": mode,
            "value": normalized_value,
            "updated_by": user["username"],
        }
    )


async def startup() -> None:
    configure_logging()
    ensure_storage()
    if not FAKETIME_PATH.exists():
        raise FileNotFoundError(f"Missing faketime control file: {FAKETIME_PATH}")
    if not APP_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Missing app template: {APP_TEMPLATE_PATH}")


@asynccontextmanager
async def lifespan(_: Starlette):
    await startup()
    yield


routes = [
    Route("/", homepage),
    Route("/app", app_page),
    Route("/health", health),
    Route("/auth/login", login, methods=["POST"]),
    Route("/auth/logout", logout, methods=["POST"]),
    Route("/auth/me", me, methods=["GET"]),
    Route("/faketime", get_faketime, methods=["GET"]),
    Route("/faketime", set_faketime, methods=["PUT"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )
]

app = Starlette(debug=False, routes=routes, middleware=middleware, lifespan=lifespan)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SIGESP faketime API and terminal helpers",
    )
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser(
        "serve",
        help="Run the Starlette service",
    )
    serve_parser.set_defaults(command="serve")

    create_user_parser = subparsers.add_parser(
        "create-user",
        help="Create a user from the terminal",
    )
    create_user_parser.add_argument(
        "--username",
        required=True,
        help="Username to create",
    )
    create_user_parser.add_argument(
        "--password",
        help="Password for the new user; if omitted, prompt securely",
    )

    return parser


def run_server() -> None:
    host = os.getenv("FAKETIME_API_HOST", "127.0.0.1")
    port = int(os.getenv("FAKETIME_API_PORT", "8080"))
    uvicorn.run("faketime_api.app:app", host=host, port=port, reload=False)


def run_create_user(username: str, password: str | None) -> int:
    ensure_storage()
    final_password = password or getpass("Password: ")
    if not final_password:
        print("Password is required.")
        return 1
    try:
        create_user(username, final_password)
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    except sqlite3.IntegrityError:
        print("Error: username already exists")
        return 1

    print(f"User created: {normalize_username(username)}")
    return 0


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.command == "create-user":
        return run_create_user(args.username, args.password)

    run_server()
    return 0
