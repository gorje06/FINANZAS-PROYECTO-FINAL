"""Cliente HTTP mínimo para Turso (libSQL remoto). Compatible con sqlite3 básico."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any


def _turso_arg(value: Any) -> dict:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "integer", "value": "1" if value else "0"}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": repr(value)}
    if isinstance(value, (bytes, bytearray)):
        return {"type": "blob", "base64": base64.b64encode(value).decode("ascii")}
    return {"type": "text", "value": str(value)}


def _normalize_cell(value: Any) -> Any:
    if isinstance(value, dict):
        if "value" in value:
            return value["value"]
        if "name" in value:
            return value["name"]
    return value


class TursoRow:
    def __init__(self, keys: list[str], values: list[Any]):
        self._keys = keys
        self._values = [_normalize_cell(v) for v in values]
        self._data = dict(zip(keys, self._values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._data[key]

    def keys(self):
        return self._keys


class TursoCursor:
    def __init__(self, conn: "TursoConnection", sql: str | None = None, params: tuple | list = ()):
        self.connection = conn
        self.lastrowid: int | None = None
        self.rowcount = 0
        self._rows: list[TursoRow] = []
        if sql is not None:
            self._execute(sql, params)

    def _execute(self, sql: str, params: tuple | list) -> None:
        result = self.connection._pipeline(
            [
                {
                    "type": "execute",
                    "stmt": {
                        "sql": sql,
                        "args": [_turso_arg(v) for v in params],
                    },
                }
            ]
        )
        payload = result[0]
        if payload.get("type") != "ok":
            error = payload.get("error") or payload
            raise RuntimeError(f"Turso error: {error}")
        body = payload["response"]["result"]
        self.rowcount = int(body.get("affected_row_count") or 0)
        last_id = _normalize_cell(body.get("last_insert_rowid"))
        self.lastrowid = int(last_id) if last_id is not None and last_id != "" else None
        cols = [c["name"] for c in body.get("cols") or []]
        raw_rows = body.get("rows") or []
        self._rows = [TursoRow(cols, row) for row in raw_rows] if cols else []

    def fetchone(self):
        if not self._rows:
            return None
        return self._rows.pop(0)

    def fetchall(self):
        rows = self._rows
        self._rows = []
        return rows

    def execute(self, sql: str, params: tuple | list = ()):
        self._execute(sql, params)
        return self

    def executemany(self, sql: str, seq_of_params):
        for params in seq_of_params:
            self._execute(sql, params)
        return self

    def executescript(self, script: str) -> "TursoCursor":
        for statement in _split_sql_script(script):
            self._execute(statement, ())
        return self


class TursoConnection:
    def __init__(self, database_url: str, auth_token: str):
        self.database_url = _https_url(database_url)
        self.auth_token = auth_token

    def _pipeline(self, requests_body: list[dict]) -> list[dict]:
        url = f"{self.database_url.rstrip('/')}/v2/pipeline"
        payload = json.dumps({"requests": requests_body}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Turso HTTP {exc.code}: {detail}") from exc
        return data.get("results") or []

    def execute(self, sql: str, params: tuple | list = ()):
        return TursoCursor(self, sql, params)

    def cursor(self):
        return TursoCursor(self)

    def executemany(self, sql: str, seq_of_params):
        cur = TursoCursor(self)
        for params in seq_of_params:
            cur = TursoCursor(self, sql, params)
        return cur

    def executescript(self, script: str) -> TursoCursor:
        cur = TursoCursor(self)
        for statement in _split_sql_script(script):
            cur = TursoCursor(self, statement)
        return cur

    def commit(self) -> None:
        return None

    def close(self) -> None:
        return None


def _https_url(database_url: str) -> str:
    url = database_url.strip()
    if url.startswith("libsql://"):
        return "https://" + url[len("libsql://") :]
    if url.startswith("https://"):
        return url
    if url.startswith("http://"):
        return url
    return "https://" + url


def _split_sql_script(script: str) -> list[str]:
    parts: list[str] = []
    for chunk in script.split(";"):
        stmt = chunk.strip()
        if stmt:
            parts.append(stmt)
    return parts


def connect_turso(database_url: str, auth_token: str) -> TursoConnection:
    if not database_url or not auth_token:
        raise ValueError("TURSO_DATABASE_URL y TURSO_AUTH_TOKEN son obligatorios.")
    return TursoConnection(database_url, auth_token)
