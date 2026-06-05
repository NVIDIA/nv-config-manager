# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
"""Stateful mock UFM REST API for the IB PKey workflows.

Implements the six endpoints exercised by the IB PKey Temporal workflows:

- GET    /ufmRest/resources/pkeys
- POST   /ufmRest/resources/pkeys/add
- GET    /ufmRest/resources/pkeys/{pkey}
- POST   /ufmRest/resources/pkeys/
- DELETE /ufmRest/resources/pkeys/{pkey}/guids/{guids_csv}
- POST   /ufmRest/resources/pkeys/{pkey}/guids/{guids_csv} (alias path used by some clients)

Plus dev helpers:

- POST /_dev/reset    - clear all in-memory state
- GET  /_dev/state    - dump current state for debugging
- GET  /healthcheck   - liveness probe

State is in-memory and per-process. Pod restart or POST /_dev/reset clears it.
Not production-grade. Not security-reviewed.
"""

from __future__ import annotations

import threading
from typing import Annotated, Any

from fastapi import Body, FastAPI, HTTPException, Path
from pydantic import BaseModel, Field


class PKeyAddRequest(BaseModel):
    """Body of POST /resources/pkeys/add (create) and POST /resources/pkeys/ (add members)."""

    pkey: str
    ip_over_ib: bool = True
    index0: bool = True
    guids: list[str] = Field(default_factory=list)
    membership: str = "full"


class _PKeyState:
    """In-memory state for a single mock PKey partition."""

    def __init__(self, *, pkey: str, ip_over_ib: bool) -> None:
        self.pkey = pkey
        self.ip_over_ib = ip_over_ib
        # Members keyed by lowercase GUID for case-insensitive comparison.
        self.guids: dict[str, dict[str, str]] = {}

    def to_summary(self) -> dict[str, Any]:
        """Match UFM's per-pkey dict shape WITHOUT guids_data."""
        return {
            "partition": f"ib-pkey-{self.pkey}",
            "ip_over_ib": self.ip_over_ib,
            "index0": True,
        }

    def to_detail(self) -> dict[str, Any]:
        """Match UFM's per-pkey dict shape WITH guids_data."""
        detail = self.to_summary()
        detail["guids"] = [
            {"guid": guid, "membership": meta.get("membership", "full")}
            for guid, meta in self.guids.items()
        ]
        return detail


class _Store:
    """Thread-safe holder for the mock state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pkeys: dict[str, _PKeyState] = {}

    def reset(self) -> None:
        with self._lock:
            self._pkeys.clear()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {pkey: state.to_detail() for pkey, state in self._pkeys.items()}

    def list_summaries(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {pkey: state.to_summary() for pkey, state in self._pkeys.items()}

    def create(self, pkey: str, *, ip_over_ib: bool) -> None:
        with self._lock:
            if pkey in self._pkeys:
                raise HTTPException(status_code=409, detail=f"PKey {pkey} already exists")
            self._pkeys[pkey] = _PKeyState(pkey=pkey, ip_over_ib=ip_over_ib)

    def get(self, pkey: str, *, with_guids: bool) -> dict[str, Any]:
        with self._lock:
            state = self._pkeys.get(pkey)
            if state is None:
                raise HTTPException(status_code=404, detail=f"PKey {pkey} not found")
            return state.to_detail() if with_guids else state.to_summary()

    def add_members(self, pkey: str, guids: list[str], membership: str) -> int:
        normalized = [g.lower() for g in guids if g]
        with self._lock:
            state = self._pkeys.get(pkey)
            if state is None:
                raise HTTPException(status_code=404, detail=f"PKey {pkey} not found")
            added = 0
            for guid in normalized:
                if guid not in state.guids:
                    added += 1
                state.guids[guid] = {"membership": membership}
            return added

    def remove_members(self, pkey: str, guids: list[str]) -> int:
        normalized = [g.lower() for g in guids if g]
        with self._lock:
            state = self._pkeys.get(pkey)
            if state is None:
                raise HTTPException(status_code=404, detail=f"PKey {pkey} not found")
            removed = 0
            for guid in normalized:
                if state.guids.pop(guid, None) is not None:
                    removed += 1
            return removed


def create_app(store: _Store | None = None) -> FastAPI:
    """Build the FastAPI app with the given (or fresh) store."""
    store = store or _Store()
    app = FastAPI(title="Mock UFM", version="0.1.0")
    app.state.store = store

    @app.get("/healthcheck")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ufmRest/resources/pkeys")
    def list_pkeys() -> dict[str, dict[str, Any]]:
        """Match UFM's dict-keyed-by-pkey response format."""
        return store.list_summaries()

    @app.post("/ufmRest/resources/pkeys/add")
    def create_pkey(payload: Annotated[PKeyAddRequest, Body()]) -> dict[str, str]:
        store.create(payload.pkey, ip_over_ib=payload.ip_over_ib)
        return {"pkey": payload.pkey, "status": "created"}

    @app.get("/ufmRest/resources/pkeys/{pkey}")
    def get_pkey(
        pkey: Annotated[str, Path()], guids_data: bool = False
    ) -> dict[str, Any]:
        return store.get(pkey, with_guids=guids_data)

    @app.post("/ufmRest/resources/pkeys/")
    @app.post("/ufmRest/resources/pkeys")
    def add_members(payload: Annotated[PKeyAddRequest, Body()]) -> dict[str, Any]:
        added = store.add_members(payload.pkey, payload.guids, payload.membership)
        return {"pkey": payload.pkey, "added": added}

    @app.delete("/ufmRest/resources/pkeys/{pkey}/guids/{guids_csv}")
    @app.post("/ufmRest/resources/pkeys/{pkey}/guids/{guids_csv}")
    def remove_members(
        pkey: Annotated[str, Path()], guids_csv: Annotated[str, Path()]
    ) -> dict[str, Any]:
        guids = [g for g in guids_csv.split(",") if g]
        removed = store.remove_members(pkey, guids)
        return {"pkey": pkey, "removed": removed}

    @app.post("/_dev/reset")
    def reset_state() -> dict[str, str]:
        store.reset()
        return {"status": "reset"}

    @app.get("/_dev/state")
    def dump_state() -> dict[str, Any]:
        return store.snapshot()

    return app


app = create_app()


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8443")),
        ssl_certfile=os.environ.get("SSL_CERTFILE"),
        ssl_keyfile=os.environ.get("SSL_KEYFILE"),
        log_level=os.environ.get("LOG_LEVEL", "info"),
    )
