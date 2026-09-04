#!/usr/bin/env python3
"""Deterministic tests for the Argo CD exact-revision convergence gate."""

import io
import json
import os
import subprocess
import tempfile
import unittest
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import requests
import responses
from wait_for_argocd import (
    Config,
    FatalApiError,
    GateFailure,
    HttpArgoApi,
    TransientApiError,
    execute_gate,
    load_config,
)

EXPECTED_CHART = "0.0.0-pr999.01234567"
EXPECTED_GIT = "0123456789abcdef0123456789abcdef01234567"
OLD_GIT = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
TEST_TOKEN = ".".join(("test-header", "test-payload", "test-signature"))
SCRIPT_DIRECTORY = Path(__file__).resolve().parent
BASE_CONFIG = Config(
    server="https://argocd.example.test",
    application="test-application",
    application_namespace="argocd",
    project="test-project",
    expected_chart_revision=EXPECTED_CHART,
    expected_git_revision=EXPECTED_GIT,
    poll_interval=1,
    sync_timeout=10,
    max_sync_attempts=2,
    max_stale_terminations=2,
    connect_timeout=10,
    request_timeout=10,
)


def application_payload(
    state: int,
    *,
    automated_prune: bool = True,
) -> dict[str, Any]:
    """Build one Application state used by the fake API."""

    stale_revisions = ["0.0.0-pr998.deadbeef", OLD_GIT]
    if state == 0:
        sync_status, health_status, phase = "OutOfSync", "Progressing", "Running"
        operation_revisions = stale_revisions
        source_count = 2
    elif state == 1:
        sync_status, health_status, phase = "OutOfSync", "Progressing", "Terminating"
        operation_revisions = stale_revisions
        source_count = 2
    elif state == 2:
        sync_status, health_status, phase = "OutOfSync", "Progressing", "Failed"
        operation_revisions = stale_revisions
        source_count = 2
    elif state == 3:
        sync_status, health_status, phase = "Synced", "Healthy", "Succeeded"
        operation_revisions = [EXPECTED_CHART, EXPECTED_GIT]
        source_count = 2
    elif state == 4:
        sync_status, health_status, phase = "Synced", "Healthy", "Succeeded"
        operation_revisions = stale_revisions
        source_count = 2
    elif state == 5:
        sync_status, health_status, phase = "OutOfSync", "Progressing", "Failed"
        operation_revisions = stale_revisions
        source_count = 3
    elif state == 6:
        sync_status, health_status, phase = "Synced", "Healthy", "Succeeded"
        operation_revisions = [EXPECTED_GIT]
        source_count = 0
    else:
        raise ValueError(f"unknown fake Application state {state}")

    sync_state: dict[str, Any] = {"status": sync_status}
    if state == 6:
        sync_state["revision"] = EXPECTED_GIT
    else:
        sync_state["revisions"] = [EXPECTED_CHART, EXPECTED_GIT]
    spec: dict[str, Any] = {"syncPolicy": {"automated": {"prune": automated_prune}}}
    if state == 6:
        spec["source"] = {}
    else:
        spec["sources"] = [{} for _ in range(source_count)]

    return {
        "spec": spec,
        "status": {
            "sync": sync_state,
            "health": {"status": health_status},
            "operationState": {
                "phase": phase,
                "operation": {"sync": {"revisions": operation_revisions}},
            },
            "resources": [],
        },
    }


class FakeClock:
    """Monotonic clock advanced only by the injected sleep function."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, duration: float) -> None:
        self.now += duration


class FakeArgoApi:
    """In-memory Argo API implementing the gate's relevant transitions."""

    def __init__(self, state: int) -> None:
        self.state = state
        self.get_attempts = 0
        self.delete_attempts = 0
        self.post_attempts = 0
        self.sync_requests: list[Mapping[str, Any]] = []
        self.automated_prune = True
        self.always_reject_sync = False
        self.converge_after_rejected_syncs = False
        self.fail_first_delete = False
        self.get_failure: Exception | None = None
        self.sync_failure: Exception | None = None
        self.synced_while_terminating = False

    def get_application(self) -> dict[str, Any]:
        self.get_attempts += 1
        if self.get_failure is not None:
            raise self.get_failure
        if self.state == 2 and self.converge_after_rejected_syncs and self.post_attempts >= 2:
            self.state = 3
        payload = application_payload(self.state, automated_prune=self.automated_prune)
        if self.state == 1:
            self.state = 2
        return payload

    def terminate_operation(self) -> None:
        self.delete_attempts += 1
        if self.fail_first_delete and self.delete_attempts == 1:
            raise TransientApiError("Argo CD API returned transient HTTP 409.")
        if self.state != 0:
            raise AssertionError(f"unexpected termination from state {self.state}")
        self.state = 1

    def start_sync(self, request: Mapping[str, Any]) -> None:
        if self.state == 1:
            self.synced_while_terminating = True
            raise TransientApiError("Argo CD API returned transient HTTP 409.")
        if self.state not in (2, 4):
            raise AssertionError(f"unexpected sync from state {self.state}")
        self.post_attempts += 1
        self.sync_requests.append(request)
        if self.sync_failure is not None:
            raise self.sync_failure
        if self.always_reject_sync or self.post_attempts == 1:
            raise TransientApiError("Argo CD API returned transient HTTP 409.")
        self.state = 3


def run_gate(
    client: FakeArgoApi,
    config: Config = BASE_CONFIG,
) -> tuple[int, str, str]:
    """Execute the gate with deterministic time and captured output."""

    clock = FakeClock()
    output = io.StringIO()
    errors = io.StringIO()
    status = execute_gate(
        config,
        client,
        monotonic=clock.monotonic,
        sleeper=clock.sleep,
        output=output,
        errors=errors,
    )
    return status, output.getvalue(), errors.getvalue()


class ArgoGateTests(unittest.TestCase):
    """Regression tests for configuration, API handling, and convergence."""

    def test_environment_target_requires_exactly_seven_fields(self) -> None:
        base_environment = os.environ.copy()
        valid = (
            "test|test-branch|test-namespace|test-release|baseline.yaml|state-dir|test-application"
        )
        environment = {**base_environment, "NVCM_TEST_ENV_TARGETS": valid}
        resolved = subprocess.run(
            ["bash", str(SCRIPT_DIRECTORY / "test_env_config.sh"), "test"],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertIn("export NVCM_ENV_ARGOCD_APPLICATION=test-application", resolved.stdout)

        malformed = [
            "test|test-branch|test-namespace|test-release|baseline.yaml|state-dir",
            f"{valid}|extra",
        ]
        for target in malformed:
            with self.subTest(target=target):
                result = subprocess.run(
                    ["bash", str(SCRIPT_DIRECTORY / "test_env_config.sh"), "test"],
                    check=False,
                    capture_output=True,
                    text=True,
                    env={**base_environment, "NVCM_TEST_ENV_TARGETS": target},
                )
                self.assertNotEqual(result.returncode, 0)

    def test_configuration_validation_and_token_removal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_directory = Path(temporary_directory)
            (project_directory / "deploy.env").write_text(
                "\n".join(
                    (
                        "ARGOCD_APPLICATION=test-application",
                        f"ARGOCD_EXPECTED_CHART_REVISION={EXPECTED_CHART}",
                        f"ARGOCD_EXPECTED_GIT_REVISION={EXPECTED_GIT}",
                    )
                ),
                encoding="utf-8",
            )
            environment = {
                "CI_PROJECT_DIR": temporary_directory,
                "NVCM_ARGOCD_SERVER": "https://argocd.example.test",
                "NVCM_ARGOCD_AUTH_TOKEN": TEST_TOKEN,
                "NVCM_ARGOCD_PROJECT": "test-project",
            }
            config, token = load_config(environment)
            self.assertEqual(config.application, "test-application")
            self.assertEqual(token, TEST_TOKEN)
            self.assertNotIn("NVCM_ARGOCD_AUTH_TOKEN", environment)

            invalid_settings = (
                ("NVCM_ARGOCD_PROJECT", ""),
                ("NVCM_ARGOCD_SERVER", "http://argocd.example.test"),
                ("NVCM_ARGOCD_POLL_INTERVAL", "0"),
                ("NVCM_ARGOCD_POLL_INTERVAL", "١٠"),
                ("NVCM_ARGOCD_SYNC_TIMEOUT", "1801"),
            )
            for name, value in invalid_settings:
                with self.subTest(name=name, value=value):
                    invalid_environment = {
                        "CI_PROJECT_DIR": temporary_directory,
                        "NVCM_ARGOCD_SERVER": "https://argocd.example.test",
                        "NVCM_ARGOCD_AUTH_TOKEN": TEST_TOKEN,
                        "NVCM_ARGOCD_PROJECT": "test-project",
                        name: value,
                    }
                    with self.assertRaises(GateFailure):
                        load_config(invalid_environment)

    def test_http_statuses_are_classified(self) -> None:
        cases = {
            302: TransientApiError,
            401: FatalApiError,
            403: FatalApiError,
            404: FatalApiError,
            409: TransientApiError,
        }
        for status, expected_error in cases.items():
            with self.subTest(status=status):
                with responses.RequestsMock() as mock:
                    mock.get(
                        "https://argocd.example.test/api/v1/applications/test-application",
                        match=[
                            responses.matchers.query_param_matcher(
                                {"appNamespace": "argocd", "project": "test-project"}
                            )
                        ],
                        status=status,
                        json={},
                        headers={"Location": "https://redirect.example.test/application"}
                        if status == 302
                        else {},
                    )
                    client = HttpArgoApi(BASE_CONFIG, TEST_TOKEN)
                    with self.assertRaises(expected_error):
                        client.get_application()
                    self.assertEqual(len(mock.calls), 1)

    def test_get_retries_transport_but_mutation_does_not(self) -> None:
        payload = json.dumps(application_payload(3)).encode()
        with responses.RequestsMock() as mock:
            application_url = "https://argocd.example.test/api/v1/applications/test-application"
            query_matcher = responses.matchers.query_param_matcher(
                {"appNamespace": "argocd", "project": "test-project"}
            )
            for _ in range(3):
                mock.get(
                    application_url,
                    match=[query_matcher],
                    body=requests.ConnectionError("network"),
                )
            mock.get(application_url, match=[query_matcher], body=payload, status=200)
            client = HttpArgoApi(BASE_CONFIG, TEST_TOKEN, sleeper=lambda _: None)
            self.assertEqual(client.get_application()["status"]["sync"]["status"], "Synced")
            self.assertEqual(len(mock.calls), 4)

        with responses.RequestsMock() as mock:
            mock.post(
                "https://argocd.example.test/api/v1/applications/test-application/sync",
                match=[
                    responses.matchers.query_param_matcher(
                        {"appNamespace": "argocd", "project": "test-project"}
                    )
                ],
                body=requests.ConnectionError("network"),
            )
            client = HttpArgoApi(BASE_CONFIG, TEST_TOKEN)
            with self.assertRaises(TransientApiError):
                client.start_sync({"revisions": [EXPECTED_CHART, EXPECTED_GIT]})
            self.assertEqual(len(mock.calls), 1)

    def test_sync_request_keeps_the_token_out_of_the_url_and_body(self) -> None:
        with responses.RequestsMock() as mock:
            mock.post(
                "https://argocd.example.test/api/v1/applications/test-application/sync",
                match=[
                    responses.matchers.query_param_matcher(
                        {"appNamespace": "argocd", "project": "test-project"}
                    )
                ],
                status=200,
                json={},
            )
            client = HttpArgoApi(BASE_CONFIG, TEST_TOKEN)
            request = {
                "revisions": [EXPECTED_CHART, EXPECTED_GIT],
                "sourcePositions": [1, 2],
            }
            client.start_sync(request)
            prepared = mock.calls[0].request
            if prepared.url is None:
                self.fail("prepared sync request has no URL")
            self.assertNotIn(TEST_TOKEN, prepared.url)
            self.assertEqual(prepared.headers["Authorization"], f"Bearer {TEST_TOKEN}")
            self.assertEqual(prepared.headers["Content-Type"], "application/json")
            if not isinstance(prepared.body, (str, bytes, bytearray)):
                self.fail("prepared sync request has no JSON body")
            self.assertEqual(json.loads(prepared.body), request)

    def test_fatal_get_stops_immediately(self) -> None:
        for status in (401, 404):
            with self.subTest(status=status):
                client = FakeArgoApi(0)
                client.get_failure = FatalApiError(f"Argo CD API returned HTTP {status}")
                result, _, errors = run_gate(client)
                self.assertEqual(result, 1)
                self.assertIn(f"HTTP {status}", errors)
                self.assertEqual(client.get_attempts, 1)

    def test_fatal_sync_stops_immediately(self) -> None:
        client = FakeArgoApi(2)
        client.sync_failure = FatalApiError("Argo CD API returned HTTP 403")
        result, _, errors = run_gate(client)
        self.assertEqual(result, 1)
        self.assertIn("HTTP 403", errors)
        self.assertEqual(client.post_attempts, 1)

    def test_rejected_syncs_are_bounded_but_external_convergence_succeeds(self) -> None:
        client = FakeArgoApi(2)
        client.always_reject_sync = True
        client.converge_after_rejected_syncs = True
        result, _, _ = run_gate(client)
        self.assertEqual(result, 0)
        self.assertEqual(client.post_attempts, 2)

    def test_exhausted_sync_budget_observes_until_timeout(self) -> None:
        client = FakeArgoApi(2)
        client.always_reject_sync = True
        config = replace(BASE_CONFIG, sync_timeout=4)
        result, output, errors = run_gate(client, config)
        self.assertEqual(result, 1)
        self.assertIn("continuing observation without further mutations", output)
        self.assertIn("timed out waiting for exact-revision Argo CD convergence", errors)
        self.assertEqual(client.post_attempts, 2)

    def test_successful_status_for_stale_operation_is_not_accepted(self) -> None:
        client = FakeArgoApi(4)
        client.always_reject_sync = True
        config = replace(BASE_CONFIG, sync_timeout=3, max_sync_attempts=1)
        result, _, errors = run_gate(client, config)
        self.assertEqual(result, 1)
        self.assertIn("timed out waiting for exact-revision Argo CD convergence", errors)
        self.assertEqual(client.post_attempts, 1)

    def test_source_revision_count_mismatch_fails_before_sync(self) -> None:
        client = FakeArgoApi(5)
        result, _, errors = run_gate(client)
        self.assertEqual(result, 1)
        self.assertIn("reports 2 resolved revisions for 3 configured sources", errors)
        self.assertEqual(client.post_attempts, 0)

    def test_single_source_application_fails_immediately(self) -> None:
        client = FakeArgoApi(6)
        result, _, errors = run_gate(client)
        self.assertEqual(result, 1)
        self.assertIn("requires a multi-source Application", errors)
        self.assertEqual(client.get_attempts, 1)
        self.assertEqual(client.post_attempts, 0)

    def test_transient_delete_does_not_consume_termination_budget(self) -> None:
        client = FakeArgoApi(0)
        client.fail_first_delete = True
        config = replace(BASE_CONFIG, max_stale_terminations=1)
        result, _, _ = run_gate(client, config)
        self.assertEqual(result, 0)
        self.assertEqual(client.state, 3)
        self.assertEqual(client.delete_attempts, 2)

    def test_sync_inherits_prune_and_maps_revisions_to_source_positions(self) -> None:
        client = FakeArgoApi(2)
        client.automated_prune = False
        result, _, _ = run_gate(client)
        self.assertEqual(result, 0)
        self.assertEqual(client.post_attempts, 2)
        self.assertEqual(
            client.sync_requests[-1],
            {
                "name": "test-application",
                "appNamespace": "argocd",
                "project": "test-project",
                "prune": False,
                "revisions": [EXPECTED_CHART, EXPECTED_GIT],
                "sourcePositions": [1, 2],
            },
        )

    def test_full_stale_operation_recovery_converges(self) -> None:
        client = FakeArgoApi(0)
        result, _, _ = run_gate(client)
        self.assertEqual(result, 0)
        self.assertEqual(client.state, 3)
        self.assertEqual(client.delete_attempts, 1)
        self.assertEqual(client.post_attempts, 2)
        self.assertFalse(client.synced_while_terminating)


if __name__ == "__main__":
    unittest.main(verbosity=2)
