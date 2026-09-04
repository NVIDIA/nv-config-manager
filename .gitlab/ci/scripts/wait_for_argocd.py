#!/usr/bin/env python3
"""Wait for exact-revision Argo CD convergence after a test promotion."""

import json
import os
import re
import sys
import time
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, TextIO, cast
from urllib.parse import quote, urlencode, urlsplit

import requests
from urllib3.util import Timeout

ACTIVE_OPERATION_PHASES = {"Running", "Pending", "Progressing", "Waiting", "Terminating"}
DNS_NAME = re.compile(r"^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$")
FULL_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
JWT = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class Config:
    """Validated runtime configuration and deployment attestation."""

    server: str
    application: str
    application_namespace: str
    project: str
    expected_chart_revision: str
    expected_git_revision: str
    poll_interval: int
    sync_timeout: int
    max_sync_attempts: int
    max_stale_terminations: int
    connect_timeout: int
    request_timeout: int


class GateFailure(Exception):
    """A fatal configuration, API, or convergence failure."""

    def __init__(self, message: str, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.payload = payload


class FatalApiError(GateFailure):
    """An API response that cannot be fixed by waiting."""


class TransientApiError(Exception):
    """An API or transport failure that can be observed and retried."""


class ArgoApi(Protocol):
    """Operations used by the convergence state machine."""

    def get_application(self, deadline: float) -> dict[str, Any]: ...

    def terminate_operation(self, deadline: float) -> None: ...

    def start_sync(self, request: Mapping[str, Any], deadline: float) -> None: ...


class HttpArgoApi:
    """Least-privilege client for one Argo CD Application."""

    def __init__(
        self,
        config: Config,
        token: str,
        *,
        session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        query = urlencode(
            {
                "appNamespace": config.application_namespace,
                "project": config.project,
            }
        )
        application = quote(config.application, safe="-.")
        self._application_url = f"{config.server}/api/v1/applications/{application}?{query}"
        self._operation_url = f"{config.server}/api/v1/applications/{application}/operation?{query}"
        self._sync_url = f"{config.server}/api/v1/applications/{application}/sync?{query}"
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "User-Agent": "nvcm-promotion-gate",
            }
        )
        self._connect_timeout = config.connect_timeout
        self._request_timeout = config.request_timeout
        self._sleeper = sleeper
        self._monotonic = monotonic
        self._application = config.application
        self._project = config.project

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: Mapping[str, Any] | None = None,
        retry_transport: bool = False,
        deadline: float,
    ) -> bytes:
        attempts = 4 if retry_transport else 1
        for attempt in range(1, attempts + 1):
            remaining = deadline - self._monotonic()
            if remaining <= 0:
                raise TransientApiError("Argo CD API deadline expired.")
            timeout = Timeout(
                total=remaining,
                connect=min(self._connect_timeout, remaining),
                read=min(self._request_timeout, remaining),
            )
            try:
                response = self._session.request(
                    method,
                    url,
                    json=json_body,
                    # Requests accepts urllib3 Timeout objects at runtime, but
                    # types-requests currently narrows this argument to scalars/tuples.
                    timeout=cast(Any, timeout),
                    allow_redirects=False,
                )
            except requests.RequestException as exc:
                if attempt < attempts:
                    remaining = deadline - self._monotonic()
                    if remaining <= 0:
                        raise TransientApiError("Argo CD API deadline expired.") from exc
                    self._sleeper(min(2, remaining))
                    continue
                raise TransientApiError(
                    f"Argo CD API transport failure after {attempt} attempt(s): "
                    f"{type(exc).__name__}."
                ) from exc

            if self._monotonic() >= deadline:
                raise TransientApiError("Argo CD API deadline expired.")

            status = response.status_code
            if 200 <= status < 300:
                return response.content
            if 300 <= status < 400:
                raise FatalApiError(
                    f"Argo CD API returned unexpected HTTP {status}; verify "
                    "NVCM_ARGOCD_SERVER is the canonical HTTPS API base URL."
                )
            if status == 401:
                raise FatalApiError(
                    "Argo CD API returned HTTP 401; the promotion token is invalid or expired."
                )
            if status == 403:
                raise FatalApiError(
                    "Argo CD API returned HTTP 403; the promotion role lacks get/sync access "
                    f"to {self._project}/{self._application}."
                )
            if status == 404:
                raise FatalApiError(
                    "Argo CD API returned HTTP 404; verify the application name, namespace, "
                    "project, and get permission."
                )
            raise TransientApiError(f"Argo CD API returned transient HTTP {status}.")

        raise AssertionError("unreachable API retry state")

    def get_application(self, deadline: float) -> dict[str, Any]:
        response = self._request(
            "GET", self._application_url, retry_transport=True, deadline=deadline
        )
        try:
            payload = json.loads(response)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TransientApiError("Argo CD API returned malformed JSON.") from exc
        if not isinstance(payload, dict):
            raise TransientApiError("Argo CD API returned malformed JSON.")
        return payload

    def terminate_operation(self, deadline: float) -> None:
        self._request("DELETE", self._operation_url, deadline=deadline)

    def start_sync(self, request: Mapping[str, Any], deadline: float) -> None:
        self._request("POST", self._sync_url, json_body=request, deadline=deadline)


def _required(environment: Mapping[str, str], name: str, message: str) -> str:
    value = environment.get(name, "").strip()
    if not value:
        raise GateFailure(message)
    return value


def _positive_integer(environment: Mapping[str, str], name: str, default: int) -> int:
    raw_value = environment.get(name, str(default))
    if not raw_value.isascii() or not raw_value.isdigit() or int(raw_value) <= 0:
        raise GateFailure(f"{name} must be a positive integer")
    return int(raw_value)


def _read_attestation(project_directory: Path) -> dict[str, str]:
    path = project_directory / "deploy.env"
    if not path.is_file():
        raise GateFailure(f"missing deployment attestation {path}")

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key not in values:
            values[key] = value

    required = (
        "ARGOCD_APPLICATION",
        "ARGOCD_EXPECTED_CHART_REVISION",
        "ARGOCD_EXPECTED_GIT_REVISION",
    )
    for key in required:
        if not values.get(key):
            raise GateFailure(f"{key} missing from deploy.env")
    return values


def load_config(environment: MutableMapping[str, str]) -> tuple[Config, str]:
    """Load and validate configuration, removing the token from the environment."""

    token = environment.pop("NVCM_ARGOCD_AUTH_TOKEN", "").strip()
    if not token:
        raise GateFailure(
            "Set NVCM_ARGOCD_AUTH_TOKEN to a protected, masked, and hidden Argo CD token"
        )

    project_directory = Path(_required(environment, "CI_PROJECT_DIR", "CI_PROJECT_DIR is required"))
    server = _required(
        environment,
        "NVCM_ARGOCD_SERVER",
        "Set NVCM_ARGOCD_SERVER to the Argo CD API base URL",
    ).rstrip("/")
    attestation = _read_attestation(project_directory)
    application = attestation["ARGOCD_APPLICATION"]
    # The chart revision is an opaque attested identifier. Its format is owned
    # by the promotion version producer; this gate only JSON-encodes and
    # compares it exactly, so duplicating the producer's format here would make
    # valid future version changes fail at deployment time.
    expected_chart_revision = attestation["ARGOCD_EXPECTED_CHART_REVISION"]
    expected_git_revision = attestation["ARGOCD_EXPECTED_GIT_REVISION"]
    application_namespace = environment.get("NVCM_ARGOCD_APPLICATION_NAMESPACE", "argocd")
    project = _required(
        environment,
        "NVCM_ARGOCD_PROJECT",
        "Set NVCM_ARGOCD_PROJECT to the Argo CD project containing the Application",
    )

    parsed_server = urlsplit(server)
    try:
        server_port = parsed_server.port
    except ValueError as exc:
        raise GateFailure("NVCM_ARGOCD_SERVER has an invalid port") from exc
    if (
        parsed_server.scheme != "https"
        or not parsed_server.hostname
        or parsed_server.username
        or parsed_server.password
        or parsed_server.query
        or parsed_server.fragment
        or (server_port is not None and not 1 <= server_port <= 65535)
    ):
        raise GateFailure("NVCM_ARGOCD_SERVER must be a valid HTTPS base URL")

    for label, value in (
        ("application name", application),
        ("application namespace", application_namespace),
        ("project", project),
    ):
        if not DNS_NAME.fullmatch(value):
            raise GateFailure(f"invalid Argo CD {label} '{value}'")
    if not FULL_GIT_SHA.fullmatch(expected_git_revision):
        raise GateFailure("expected Git revision is not a full SHA-1")
    if not JWT.fullmatch(token):
        raise GateFailure("NVCM_ARGOCD_AUTH_TOKEN must be an Argo CD JWT")

    poll_interval = _positive_integer(environment, "NVCM_ARGOCD_POLL_INTERVAL", 10)
    sync_timeout = _positive_integer(environment, "NVCM_ARGOCD_SYNC_TIMEOUT", 1800)
    max_sync_attempts = _positive_integer(environment, "NVCM_ARGOCD_MAX_SYNC_ATTEMPTS", 2)
    max_stale_terminations = _positive_integer(environment, "NVCM_ARGOCD_MAX_STALE_TERMINATIONS", 2)
    connect_timeout = _positive_integer(environment, "NVCM_ARGOCD_CONNECT_TIMEOUT", 10)
    request_timeout = _positive_integer(environment, "NVCM_ARGOCD_REQUEST_TIMEOUT", 60)
    if sync_timeout > 1800:
        raise GateFailure(
            "NVCM_ARGOCD_SYNC_TIMEOUT must not exceed 1800 seconds so the 35-minute job "
            "retains diagnostic headroom"
        )
    request_timeout = min(request_timeout, sync_timeout)
    connect_timeout = min(connect_timeout, request_timeout)

    return (
        Config(
            server=server,
            application=application,
            application_namespace=application_namespace,
            project=project,
            expected_chart_revision=expected_chart_revision,
            expected_git_revision=expected_git_revision,
            poll_interval=poll_interval,
            sync_timeout=sync_timeout,
            max_sync_attempts=max_sync_attempts,
            max_stale_terminations=max_stale_terminations,
            connect_timeout=connect_timeout,
            request_timeout=request_timeout,
        ),
        token,
    )


def _nested(payload: Mapping[str, Any], *keys: str) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _status(payload: Mapping[str, Any], *keys: str, default: str) -> str:
    value = _nested(payload, *keys)
    return value if isinstance(value, str) and value else default


def _string_list(payload: Mapping[str, Any], *keys: str) -> list[str]:
    value = _nested(payload, *keys)
    if not isinstance(value, list):
        return []
    revisions = [item for item in value if isinstance(item, str)]
    return revisions if len(revisions) == len(value) else []


def _operation_revisions(payload: Mapping[str, Any]) -> list[str]:
    revisions = _string_list(payload, "status", "operationState", "operation", "sync", "revisions")
    legacy_revision = _nested(payload, "status", "operationState", "operation", "sync", "revision")
    if isinstance(legacy_revision, str) and legacy_revision:
        revisions.append(legacy_revision)
    return revisions


def _matches_expected(revisions: list[str], config: Config) -> bool:
    return config.expected_chart_revision in revisions and config.expected_git_revision in revisions


def _automated_prune(payload: Mapping[str, Any]) -> bool:
    return _nested(payload, "spec", "syncPolicy", "automated", "prune") is True


def _source_count(payload: Mapping[str, Any]) -> int:
    sources = _nested(payload, "spec", "sources")
    return len(sources) if isinstance(sources, list) else 0


def _diagnostics(payload: Mapping[str, Any]) -> dict[str, Any]:
    resources = _nested(payload, "status", "resources")
    unconverged: list[dict[str, Any]] = []
    if isinstance(resources, list):
        for resource in resources:
            if not isinstance(resource, Mapping):
                continue
            resource_health = _nested(resource, "health", "status")
            if resource.get("status", "Unknown") == "Synced" and (
                resource_health in (None, "Healthy")
            ):
                continue
            unconverged.append(
                {
                    key: resource.get(key)
                    for key in ("group", "kind", "namespace", "name", "status", "health")
                }
            )

    return {
        "sync": _nested(payload, "status", "sync"),
        "health": _nested(payload, "status", "health"),
        "operation": {
            "phase": _nested(payload, "status", "operationState", "phase"),
            "message": _nested(payload, "status", "operationState", "message"),
            "startedAt": _nested(payload, "status", "operationState", "startedAt"),
            "finishedAt": _nested(payload, "status", "operationState", "finishedAt"),
            "revisions": _nested(
                payload, "status", "operationState", "operation", "sync", "revisions"
            ),
        },
        "conditions": _nested(payload, "status", "conditions") or [],
        "unconvergedResources": unconverged,
    }


def _sleep_before_deadline(
    duration: float,
    deadline: float,
    monotonic: Callable[[], float],
    sleeper: Callable[[float], None],
) -> bool:
    """Sleep for no longer than the remaining budget and report time remaining."""

    remaining = deadline - monotonic()
    if remaining <= 0:
        return False
    sleeper(min(duration, remaining))
    return monotonic() < deadline


def wait_for_convergence(
    config: Config,
    client: ArgoApi,
    *,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    output: TextIO = sys.stdout,
) -> None:
    """Observe and safely recover one Application until exact convergence."""

    deadline = monotonic() + config.sync_timeout
    sync_attempts = 0
    stale_terminations = 0
    sync_budget_exhausted_reported = False
    previous_summary = ""
    last_payload: dict[str, Any] | None = None

    print(
        f"Waiting for Argo CD application {config.application_namespace}/{config.application}:",
        file=output,
    )
    print(f"  chart: {config.expected_chart_revision}", file=output)
    print(f"  values revision: {config.expected_git_revision}", file=output)

    while monotonic() < deadline:
        try:
            payload = client.get_application(deadline)
        except TransientApiError as exc:
            print(str(exc), file=output)
            print(
                f"Argo CD API query failed; retrying in {config.poll_interval}s...",
                file=output,
            )
            if not _sleep_before_deadline(config.poll_interval, deadline, monotonic, sleeper):
                break
            continue
        last_payload = payload

        if _source_count(payload) == 0:
            raise GateFailure(
                f"Argo CD application {config.application} declares no spec.sources; "
                "the exact-revision gate requires a multi-source Application",
                last_payload,
            )

        sync_status = _status(payload, "status", "sync", "status", default="Unknown")
        health_status = _status(payload, "status", "health", "status", default="Unknown")
        operation_phase = _status(payload, "status", "operationState", "phase", default="None")
        summary = f"sync={sync_status}, health={health_status}, operation={operation_phase}"
        if summary != previous_summary:
            print(f"  {summary}", file=output)
            previous_summary = summary

        desired_revisions = _string_list(payload, "status", "sync", "revisions")
        desired_matches = _matches_expected(desired_revisions, config)
        operation_matches = _matches_expected(_operation_revisions(payload), config)

        if (
            desired_matches
            and operation_matches
            and sync_status == "Synced"
            and health_status == "Healthy"
            and operation_phase == "Succeeded"
        ):
            print("Argo CD synced and health-checked the exact promoted revisions.", file=output)
            return

        operation_active = operation_phase in ACTIVE_OPERATION_PHASES
        if (
            desired_matches
            and operation_active
            and operation_phase != "Terminating"
            and not operation_matches
        ):
            if stale_terminations >= config.max_stale_terminations:
                raise GateFailure(
                    f"Argo CD repeatedly started stale operations for {config.application}",
                    last_payload,
                )
            next_termination = stale_terminations + 1
            print(
                "Terminating stale Argo CD operation "
                f"({next_termination}/{config.max_stale_terminations})...",
                file=output,
            )
            try:
                client.terminate_operation(deadline)
            except TransientApiError as exc:
                print(str(exc), file=output)
                print(
                    "Argo CD rejected stale-operation termination; will retry.",
                    file=output,
                )
            else:
                stale_terminations = next_termination
                print(
                    "Stale Argo CD operation terminated "
                    f"({stale_terminations}/{config.max_stale_terminations}).",
                    file=output,
                )
            if not _sleep_before_deadline(config.poll_interval, deadline, monotonic, sleeper):
                break
            continue

        if (
            desired_matches
            and not operation_active
            and (sync_status != "Synced" or not operation_matches)
        ):
            if sync_attempts >= config.max_sync_attempts:
                if not sync_budget_exhausted_reported:
                    print(
                        "Exact-revision sync attempt limit reached; continuing observation "
                        "without further mutations.",
                        file=output,
                    )
                    sync_budget_exhausted_reported = True
            else:
                source_count = _source_count(payload)
                revision_count = len(desired_revisions)
                if source_count != revision_count:
                    raise GateFailure(
                        f"Argo CD reports {revision_count} resolved revisions for "
                        f"{source_count} configured sources; refusing a positional sync",
                        last_payload,
                    )

                sync_attempts += 1
                prune = _automated_prune(payload)
                request = {
                    "name": config.application,
                    "appNamespace": config.application_namespace,
                    "project": config.project,
                    "prune": prune,
                    "revisions": desired_revisions,
                    "sourcePositions": list(range(1, revision_count + 1)),
                }
                print(
                    "Starting exact-revision Argo CD sync "
                    f"({sync_attempts}/{config.max_sync_attempts}, prune={str(prune).lower()})...",
                    file=output,
                )
                try:
                    client.start_sync(request, deadline)
                except TransientApiError as exc:
                    print(str(exc), file=output)
                    print(
                        f"Argo CD did not accept sync attempt {sync_attempts}; "
                        "observing state before any retry.",
                        file=output,
                    )

        if not _sleep_before_deadline(config.poll_interval, deadline, monotonic, sleeper):
            break

    raise GateFailure(
        f"timed out waiting for exact-revision Argo CD convergence for {config.application}",
        last_payload,
    )


def execute_gate(
    config: Config,
    client: ArgoApi,
    *,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    output: TextIO = sys.stdout,
    errors: TextIO = sys.stderr,
) -> int:
    """Run the gate and render bounded, token-free failure diagnostics."""

    try:
        wait_for_convergence(
            config,
            client,
            monotonic=monotonic,
            sleeper=sleeper,
            output=output,
        )
    except GateFailure as exc:
        print(f"ERROR: {exc}", file=errors)
        if exc.payload is not None:
            print(json.dumps(_diagnostics(exc.payload), indent=2), file=errors)
        return 1
    return 0


def main() -> int:
    """CLI entry point."""

    try:
        config, token = load_config(os.environ)
    except GateFailure as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    client = HttpArgoApi(config, token)
    return execute_gate(config, client)


if __name__ == "__main__":
    raise SystemExit(main())
