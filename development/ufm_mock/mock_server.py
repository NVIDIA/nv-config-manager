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
- PUT    /ufmRest/resources/pkeys/    (atomic set/overwrite, create-on-missing)
- DELETE /ufmRest/resources/pkeys/{pkey}/guids/{guids_csv}
- POST   /ufmRest/resources/pkeys/{pkey}/guids/{guids_csv} (alias path used by some clients)

Like real UFM, a partition is auto-removed once its last member is removed, so a
subsequent GET of that pkey returns 404.

Plus read-only inventory endpoints backed by captured fixtures (when mounted):

- GET    /ufmRest/resources/ports    - IB Port GUID Discovery
- GET    /ufmRest/resources/systems  - fabric inventory

Plus dev helpers:

- POST /_dev/reset    - clear all in-memory state
- GET  /_dev/state    - dump current state for debugging
- GET  /healthcheck   - liveness probe

State is in-memory and per-process. Pod restart or POST /_dev/reset clears it.
Not production-grade. Not security-reviewed.
"""

from __future__ import annotations

import gzip
import json
import os
import threading
from pathlib import Path as FsPath
from typing import Annotated, Any

import uvicorn
from fastapi import Body, FastAPI, HTTPException, Path
from pydantic import BaseModel, Field


def _load_fixture(name: str) -> list[dict[str, Any]]:
    """Load a read-only UFM fixture list (``<name>.json`` or ``<name>.json.gz``).

    Returns an empty list when the fixture is absent so unit tests that run
    without mounted fixtures still get a valid (empty) response.
    """
    base = FsPath(os.environ.get("FIXTURES_DIR", "/app/fixtures"))
    for candidate in (base / f"{name}.json.gz", base / f"{name}.json"):
        if not candidate.exists():
            continue
        raw = candidate.read_bytes()
        if candidate.suffix == ".gz":
            raw = gzip.decompress(raw)
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    return []


class PKeyAddRequest(BaseModel):
    """Body of POST /resources/pkeys/add (create) and POST/PUT /resources/pkeys/.

    Mirrors UFM 6.19.x semantics: ``membership`` is a single string applied to every
    GUID; the plural ``memberships`` is an index-aligned per-GUID list. The two
    endpoints treat the plural array differently (see
    ``_memberships_add``/``_memberships_set``).
    """

    pkey: str
    ip_over_ib: bool = True
    index0: bool = True
    guids: list[str] = Field(default_factory=list)
    membership: str = "full"
    memberships: list[str] | None = None


def _memberships_add(req: PKeyAddRequest) -> list[str]:
    """POST/Add: UFM ignores the plural ``memberships``; the single ``membership`` applies to all."""
    return [req.membership] * len(req.guids)


def _memberships_set(req: PKeyAddRequest) -> list[str]:
    """PUT/Set: UFM honors the index-aligned ``memberships`` list, else the single ``membership``."""
    if req.memberships is not None:
        if len(req.memberships) != len(req.guids):
            raise HTTPException(
                status_code=400,
                detail="memberships length must match guids length",
            )
        return list(req.memberships)
    return [req.membership] * len(req.guids)


class _PKeyState:
    """In-memory state for a single mock PKey partition."""

    def __init__(self, *, pkey: str, ip_over_ib: bool, index0: bool) -> None:
        self.pkey = pkey
        self.ip_over_ib = ip_over_ib
        self.index0 = index0
        # Members keyed by lowercase GUID for case-insensitive comparison.
        self.guids: dict[str, dict[str, str]] = {}

    def to_summary(self) -> dict[str, Any]:
        """Match UFM's per-pkey dict shape WITHOUT guids_data."""
        return {
            "partition": f"ib-pkey-{self.pkey}",
            "ip_over_ib": self.ip_over_ib,
            "index0": self.index0,
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

    def create(self, pkey: str, *, ip_over_ib: bool, index0: bool) -> None:
        with self._lock:
            if pkey in self._pkeys:
                raise HTTPException(status_code=409, detail=f"PKey {pkey} already exists")
            self._pkeys[pkey] = _PKeyState(pkey=pkey, ip_over_ib=ip_over_ib, index0=index0)

    def get(self, pkey: str, *, with_guids: bool) -> dict[str, Any]:
        with self._lock:
            state = self._pkeys.get(pkey)
            if state is None:
                raise HTTPException(status_code=404, detail=f"PKey {pkey} not found")
            return state.to_detail() if with_guids else state.to_summary()

    def set_members(
        self,
        pkey: str,
        guids: list[str],
        memberships: list[str],
        *,
        ip_over_ib: bool,
        index0: bool,
    ) -> int:
        """Atomically replace a partition's member list, mirroring UFM's PUT.

        Creates the partition if absent (UFM's create-on-missing) and overwrites
        the entire member list in one step. ``memberships`` is index-aligned with
        ``guids``, giving per-GUID membership.
        """
        pairs = [(g.lower(), m) for g, m in zip(guids, memberships, strict=False) if g]
        with self._lock:
            state = self._pkeys.get(pkey)
            if state is None:
                state = _PKeyState(pkey=pkey, ip_over_ib=ip_over_ib, index0=index0)
                self._pkeys[pkey] = state
            # UFM's PUT overwrites the whole partition, so refresh flags too,
            # not just the member list, even when the partition already exists.
            state.ip_over_ib = ip_over_ib
            state.index0 = index0
            state.guids = {guid: {"membership": membership} for guid, membership in pairs}
            return len(state.guids)

    def add_members(self, pkey: str, guids: list[str], memberships: list[str]) -> int:
        pairs = [(g.lower(), m) for g, m in zip(guids, memberships, strict=False) if g]
        with self._lock:
            state = self._pkeys.get(pkey)
            if state is None:
                raise HTTPException(status_code=404, detail=f"PKey {pkey} not found")
            added = 0
            for guid, membership in pairs:
                if guid not in state.guids:
                    added += 1
                state.guids[guid] = {"membership": membership}
            return added

    def remove_members(self, pkey: str, guids: list[str]) -> tuple[int, bool]:
        """Remove members and, mirroring UFM, drop the partition once it is empty.

        Real UFM deletes a PKey partition when its last member is removed. The
        partition is only removed when a removal actually empties it, so a no-op
        delete (or a delete against an already-empty partition) leaves it intact,
        matching UFM's create-then-add-members window.

        Returns ``(removed_count, pkey_removed)``.
        """
        normalized = [g.lower() for g in guids if g]
        with self._lock:
            state = self._pkeys.get(pkey)
            if state is None:
                raise HTTPException(status_code=404, detail=f"PKey {pkey} not found")
            removed = 0
            for guid in normalized:
                if state.guids.pop(guid, None) is not None:
                    removed += 1
            pkey_removed = removed > 0 and not state.guids
            if pkey_removed:
                del self._pkeys[pkey]
            return removed, pkey_removed


def create_app(store: _Store | None = None) -> FastAPI:
    """Build the FastAPI app with the given (or fresh) store."""
    store = store or _Store()
    app = FastAPI(title="Mock UFM", version="0.1.0")
    app.state.store = store

    # Read-only inventory fixtures captured from a real UFM fabric. Used by the
    # IB Port GUID Discovery workflow (ports) and for fabric realism (systems).
    ports_fixture = _load_fixture("ports")
    systems_fixture = _load_fixture("systems")

    @app.get("/healthcheck")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ufmRest/resources/ports")
    def list_ports() -> list[dict[str, Any]]:
        """Return the captured UFM port inventory (bare list, as UFM does)."""
        return ports_fixture

    @app.get("/ufmRest/resources/systems")
    def list_systems() -> list[dict[str, Any]]:
        """Return the captured UFM systems inventory."""
        return systems_fixture

    @app.get("/ufmRest/resources/pkeys")
    def list_pkeys() -> dict[str, dict[str, Any]]:
        """Match UFM's dict-keyed-by-pkey response format."""
        return store.list_summaries()

    @app.post("/ufmRest/resources/pkeys/add")
    def create_pkey(payload: Annotated[PKeyAddRequest, Body()]) -> dict[str, str]:
        store.create(payload.pkey, ip_over_ib=payload.ip_over_ib, index0=payload.index0)
        return {"pkey": payload.pkey, "status": "created"}

    @app.get("/ufmRest/resources/pkeys/{pkey}")
    def get_pkey(pkey: Annotated[str, Path()], guids_data: bool = False) -> dict[str, Any]:
        return store.get(pkey, with_guids=guids_data)

    @app.post("/ufmRest/resources/pkeys/")
    @app.post("/ufmRest/resources/pkeys")
    def add_members(payload: Annotated[PKeyAddRequest, Body()]) -> dict[str, Any]:
        memberships = _memberships_add(payload)
        added = store.add_members(payload.pkey, payload.guids, memberships)
        return {"pkey": payload.pkey, "added": added}

    @app.put("/ufmRest/resources/pkeys/")
    @app.put("/ufmRest/resources/pkeys")
    def set_members(payload: Annotated[PKeyAddRequest, Body()]) -> dict[str, Any]:
        memberships = _memberships_set(payload)
        count = store.set_members(
            payload.pkey,
            payload.guids,
            memberships,
            ip_over_ib=payload.ip_over_ib,
            index0=payload.index0,
        )
        return {"pkey": payload.pkey, "guids_set": count}

    @app.delete("/ufmRest/resources/pkeys/{pkey}/guids/{guids_csv}")
    @app.post("/ufmRest/resources/pkeys/{pkey}/guids/{guids_csv}")
    def remove_members(
        pkey: Annotated[str, Path()], guids_csv: Annotated[str, Path()]
    ) -> dict[str, Any]:
        guids = [g for g in guids_csv.split(",") if g]
        removed, pkey_removed = store.remove_members(pkey, guids)
        return {"pkey": pkey, "removed": removed, "pkey_removed": pkey_removed}

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
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8443")),
        ssl_certfile=os.environ.get("SSL_CERTFILE"),
        ssl_keyfile=os.environ.get("SSL_KEYFILE"),
        log_level=os.environ.get("LOG_LEVEL", "info"),
    )
