# Mock UFM for IB PKey workflow development

A stateful in-cluster mock of the UFM REST API. Use when you want to run the
real IB PKey Temporal workflows against the real Nautobot but cannot reach
(or do not want to involve) a real UFM.

## What this does

Deploys three things into the `nv-config-manager` namespace:

1. `Deployment/ufm-mock` running a small FastAPI app
2. `Service/ufm-mock` exposing port 443 inside the cluster
3. An update to `Secret/nv-config-manager-ini` adding a `[ufm]` section so
   `UFMClient` finds credentials

The FastAPI app implements the six UFM REST endpoints the IB PKey workflows
actually call:

| Method | Path | Used by |
| ------ | ---- | ------- |
| `GET`    | `/ufmRest/resources/pkeys` | `validate_pkey_available` |
| `POST`   | `/ufmRest/resources/pkeys/add` | `create_pkey_on_ufm` |
| `GET`    | `/ufmRest/resources/pkeys/{pkey}` | `verify_pkey_created`, `fetch_pkey_members`, `verify_pkey_members` |
| `POST`   | `/ufmRest/resources/pkeys/` | `add_guids_to_pkey` |
| `DELETE` | `/ufmRest/resources/pkeys/{pkey}/guids/{guids_csv}` | `remove_guids_from_pkey` |
| `GET`    | `/healthcheck` | readiness/liveness |

Plus two dev helpers:

- `POST /_dev/reset` clears all in-memory state
- `GET  /_dev/state` dumps current state as JSON

State lives in process memory only. Pod restart or `/_dev/reset` clears it.

## Usage

```bash
make ufm-mock-up
```

Wait ~30s for the worker rollout to complete, then in the IB PKey workflow
form put the mock hostname into the `host` field:

```text
ufm-mock.nv-config-manager.svc.cluster.local
```

Leave the `site` field blank, or set it to anything (the mock ignores it).
Run the workflow. The workflow will:

1. Hit the mock UFM over HTTPS (cert is self-signed; `UFMClient` skips
   validation by passing `ssl=False`).
2. Add a partition / GUIDs / members in mock memory.
3. Write the real overlay and PKey records to Nautobot.

Other targets:

```bash
make ufm-mock-state     # dump current mock state
make ufm-mock-reset     # clear state without restarting the pod
make ufm-mock-down      # remove the Deployment, Service, and ConfigMap
```

## Verifying it works

After running an IB PKey workflow that includes a `location_name`, check
Nautobot's Overlays plugin to see the `Overlay` and `InfiniBandPKey` records
that were just written. The mock state should also reflect the same PKey:

```bash
make ufm-mock-state
```

## Things to know

- Helm-driven re-deploys (`make local-up`, `make kind-up`) overwrite the
  `nv-config-manager-ini` Secret and wipe the `[ufm]` section. Re-run
  `make ufm-mock-up` after any redeploy to inject creds again.
- `Secret/nv-config-manager-ini` only carries the `[ufm]` global section; this
  mock is not site-scoped. The IB PKey workflows do not require a site, so the
  global section suffices.
- The cert is generated fresh on every pod start by an init container running
  `alpine/openssl`. The cert is never validated by the worker.
- The mock pod runs as non-root with `readOnlyRootFilesystem: true`. Python
  package installs go to `/tmp/pylib` (writable emptyDir). Total cold start
  time is ~20–30s due to the pip install at boot. If you want faster restarts,
  bake the dependencies into a pre-built image.
- This is not production-grade. It accepts any BasicAuth credentials, has no
  rate limiting, and stores state in a single Python dict.

## Files

| File | Purpose |
| ---- | ------- |
| `mock_server.py` | FastAPI app implementing the UFM endpoints |
| `test_mock_server.py` | pytest unit tests (run with `uv run pytest deploy/dev/ufm-mock/`) |
| `manifest.yaml` | Deployment + Service definitions (uses `${NAMESPACE}` envsubst placeholder) |
| `inject-ufm-creds.sh` | Patches `nv-config-manager-ini` with a `[ufm]` section |
