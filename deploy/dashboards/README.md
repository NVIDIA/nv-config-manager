# Grafana Dashboards — Staging Copies

Dashboard JSON files here mirror what lives (or will live) in the dashboards repo:

> `gitlab-master.nvidia.com/nsv-network/gni-dev/observability/deploy/dashboards`
> (local clone: `/Users/kiwueke/Documents/dashboards`)

The dashboards repo is synced into Panoptes Grafana via ArgoCD. All dashboards land
in the **Provisioned** folder (read-only) and an editable copy is automatically created
in the **Staging** folder.

---

## How the dashboards repo works

All dashboard JSON files live **flat** under `ngc-network-dashboards/` — no subfolders.
The Helm template (`templates/gen-dashboards.yaml`) wraps each JSON into a `GrafanaDashboard`
CR and:
- Replaces `[[.datasourceName]]` with the per-Grafana-instance default datasource UID
  (Promxy Geo Aggregator on the main instance; `mimir-local` on regional instances)
- Injects the `"provisioned"` tag automatically
- Sets `folderUID: provisioned-dashboards`

**Do not use `${datasource}` Grafana template variables** — datasource wiring is done
via the `[[.datasourceName]]` / `[[.datasourceUID.<name>]]` placeholder system at deploy time.

---

## Workflow for adding / updating a dashboard

### Option A — preferred (Grafana Staging UI)

1. Go to `https://dashboards.telemetry.dgxc.ngc.nvidia.com`, navigate to **Staging** folder.
2. Create or edit your dashboard, add relevant tags, save.
3. Click **Publish Changes** (or trigger the `sync-from-staging` pipeline manually on GitLab).
4. A GitLab MR is created automatically — review and merge.
5. ArgoCD auto-syncs within ~2 minutes; dashboard appears in **Provisioned** folder.

Use this path when metrics are already flowing (i.e., after `temporal.observability.enabled: true`
is deployed and data is visible in Staging).

### Option B — direct Git (used for GNINWD-1588)

1. Place the JSON in `ngc-network-dashboards/<dashboard-name>.json` in the dashboards repo.
2. Run `bash scripts/validate-dashboards.sh` — must pass with 0 errors.
3. Open an MR to `main`.
4. ArgoCD auto-syncs on merge.

Rules for direct Git JSON:
- `"editable": false`
- `"uid"`: non-empty, unique across all files in `ngc-network-dashboards/`
- `"tags"`: at least one tag (e.g. `["temporal", "kiwi", "nv-config-manager", "gni"]`)
- Datasource UIDs: use `[[.datasourceName]]` (Promxy Geo Aggregator / mimir-local on regional)
  or named placeholders like `[[.datasourceUID.mimir-us-east-1]]`
- No `.id` or `.version` fields

---

## Files in this directory

| File | Destination in dashboards repo | Ticket |
|------|-------------------------------|--------|
| `kiwi-temporal/temporal-workflow-health.json` | `ngc-network-dashboards/kiwi-temporal-workflow-health.json` | GNINWD-1588 |

The file here is the authoritative copy. The dashboards repo copy at
`ngc-network-dashboards/kiwi-temporal-workflow-health.json` must stay in sync with it.
