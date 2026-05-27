# NV Config Manager Templates

Template rendering engine, public reference templates, and plugin host for NV
Config Manager render services.

This package is published as the `nv-config-manager-templates` Python
distribution. It is versioned from the repository Git tag so it can match the
platform release while still being consumed independently by render services and
external template plugin packages.

## Render Model

The render engine is intentionally small:

1. It loads device data from Nautobot using the core device GraphQL query.
2. It resolves the device's site or plugin-provided location name.
3. It loads location data using the core location GraphQL query.
4. It executes any plugin GraphQL queries and stores the results by query name.
5. It selects every entrypoint template under:

   ```text
   <normalized-platform>/<normalized-role>/<desired-firmware>/entrypoint/
   ```

6. It renders each entrypoint with this Jinja context:

   ```text
   device_data   # core device query result
   location_data # core location query result
   plugin_data   # optional plugin query results, keyed by query name
   ```

The platform and role path components are normalized by lower-casing and
replacing whitespace with hyphens. For example, platform `Cumulus Linux`, role
`Storage Leaf`, and firmware `5.16.1` select templates below:

```text
cumulus-linux/storage-leaf/5.16.1/entrypoint/
```

## Template Tree

Reference templates live under:

```text
src/nv_config_manager_templates/templates/
```

The expected shape is:

```text
<platform>/
  <role>/
    base/
      <shared full-file template>.j2
    include/
      <shared partial>.j2
    <firmware-version>/
      entrypoint/
        <rendered output file>.j2
      include/
        <version-specific partial>.j2
```

Use these directory names consistently:

- `entrypoint/` contains top-level rendered files. The renderer discovers these
  and produces one output file per entrypoint.
- `base/` contains reusable skeletons with Jinja blocks.
- `include/` contains partials intended to be included or overridden by a role
  or firmware-specific template.
- `<firmware-version>/include/` contains only behavior that truly differs for
  that firmware version.

Entrypoint filenames should include the output file extension plus `.j2`, such
as `startup.yaml.j2`, `boot-script.j2`, `full-config.j2`,
`ztp.json.j2`, or `nmx-commands.txt.j2`.

## Template Design Principles

### Prefer Inheritance and Small Overrides

Use Jinja inheritance as the primary way to keep templates DRY. Start with the
most common parent template, then override the smallest useful block.

Preferred pattern:

```jinja
{% extends "cumulus-linux/leaf-common/base/startup.yaml.j2" %}

{% block interfaces %}
{% include "cumulus-linux/storage-leaf/5.16.1/include/interface.j2" %}
{% endblock interfaces %}
```

Avoid copying a complete `startup.yaml.j2` just to change one section. Copying
full files makes firmware changes, bug fixes, and schema updates fan out across
many roles. A role-specific template should contain only role-specific behavior;
a version-specific template should contain only version-specific behavior.

Common inheritance layers should generally flow from broad to narrow:

```text
platform role_common -> common family role -> concrete role -> firmware version
```

For example, a Cumulus leaf role should reuse `role_common` and
`leaf-common` behavior where possible, then override only the concrete leaf
blocks that differ.

### Treat Entrypoints as Thin Composition

Entrypoints should compose reusable blocks and includes. They should not become
large data-processing files.

Good entrypoints answer:

- Which rendered files exist for this platform, role, and firmware?
- Which base skeleton is used?
- Which blocks are overridden for this version?

They should not answer:

- How is a Nautobot object shaped?
- How are interfaces sorted or filtered?
- How do we recover from missing source data?

Those questions belong in Python filters and dataclasses.

### No Direct GraphQL Access in Templates Ever

Templates must not call GraphQL, embed GraphQL queries, or depend on
GraphQL-shaped response paths directly. All Nautobot data access must go through
filter wrappers or dataclass wrappers.

Use:

```jinja
{% for intf in device_data|interfaces(prefix="swp") %}
  {{ intf.name }}:
{% endfor %}
```

Do not add new template logic that reaches through raw GraphQL dictionaries:

```jinja
{# Do not add new code like this. #}
{% for intf in device_data.data.device.interfaces %}
```

This boundary is deliberate. Nautobot GraphQL schemas, plugin fields, and query
shape can change. When templates only call wrappers such as `interfaces`,
`interface_by_name`, `site_name`, `asn`, `site_aggregates`, or plugin-owned
filters, an upstream API change can be handled in one Python wrapper instead of
touching every template that happens to read the old field path.

If a template needs data that no wrapper exposes:

1. Add or adjust the core GraphQL query, or add a plugin query when the data is
   plugin-owned.
2. Add a filter or dataclass property that returns the stable concept the
   template needs.
3. Add unit tests for the wrapper.
4. Update the template to call the wrapper.

Plugin query data follows the same rule. `plugin_data` is available in the
render context, but templates should not hard-code plugin GraphQL response
paths. Expose plugin-owned concepts through plugin filters so schema changes
remain isolated to the plugin.

### Keep Data Logic in Python

Use Python filters for sorting, filtering, validation, fallback handling, and
object conversion. Templates should stay close to output formatting.

Filters should:

- Return stable domain objects or simple values.
- Raise `FilterException` when required data is missing or inconsistent.
- Provide explicit optional behavior, such as `fail_if_missing=False`, only when
  the rendered configuration is valid without that data.
- Sort collections deterministically before returning them when output order
  matters.

Templates should:

- Call filters for domain concepts.
- Format target-native output.
- Use blocks and includes for composition.
- Fail loudly by letting wrapper exceptions propagate.

### Namespace Common Templates

Common templates should be named for the domain they serve. Built-in generic
Cumulus behavior lives under `cumulus-linux/role_common`. More specific common
families use names such as `leaf-common`, `spine-common`, or
`superpod-common`.

Plugins should use their own common role names instead of adding broad names
that could be mistaken for built-in template ownership. This keeps inheritance
clear and makes accidental shadowing easier to detect.

### Be Deliberate With Firmware Versions

A firmware directory is a compatibility boundary. Add files under
`<version>/include/` or `<version>/entrypoint/` only when that firmware truly
needs different rendered output.

When a new firmware release mostly matches an existing release, prefer:

```jinja
{% extends "cumulus-linux/<role>/<previous-version>/entrypoint/startup.yaml.j2" %}
```

or a base/common template override rather than duplicating every include.

### Validate Rendered Outputs

Render tests should use cached Nautobot fixtures and expected output files under
`tests/resources/`. For YAML entrypoints, tests should parse the rendered output
with `yaml.safe_load` so syntax failures are caught before deployment.

When adding a role, platform, firmware version, or plugin template tree, add
fixtures that cover at least one representative device and every rendered
entrypoint.

## Built-In Filters

The engine dynamically loads public functions from these built-in filter
modules:

```text
nv_config_manager_templates.filters.bgp
nv_config_manager_templates.filters.device
nv_config_manager_templates.filters.ip
nv_config_manager_templates.filters.location
nv_config_manager_templates.filters.vault
```

Filter names are the Jinja filter names. A function named `interfaces` is used
as:

```jinja
{{ device_data|interfaces(prefix="swp") }}
```

Built-in filter name conflicts are treated as errors. Plugin filter conflicts
with built-in filters are skipped with a warning, so plugins cannot silently
replace core wrapper behavior.

## Plugin Architecture

Template plugins are normal Python packages that register an entry point in the
`nv_config_manager_templates.plugins` group. At runtime the renderer discovers
installed plugins, imports their modules, asks them for optional hooks, and adds
their templates, filters, and query data to the render environment.

Minimal plugin registration:

```toml
[project.entry-points."nv_config_manager_templates.plugins"]
my-plugin = "my_template_plugin"
```

Minimal plugin module:

```python
from pathlib import Path
from typing import Any

from my_template_plugin.filters import get_custom_filters as _get_custom_filters


def get_template_paths() -> list[Path]:
    return [Path(__file__).parent / "templates"]


def get_custom_filters() -> dict[str, Any]:
    return _get_custom_filters()


def get_graphql_queries() -> dict[str, str]:
    return {}
```

All plugin hooks are optional. A plugin can provide only templates, only
filters, only queries, or any combination of those capabilities.

### Discovery and Load Order

Renderer initialization performs this sequence:

1. Read installed entry points from `nv_config_manager_templates.plugins`.
2. Import each plugin module.
3. Call `get_template_paths()` when present.
4. Call `get_custom_filters()` when present.
5. Call `get_graphql_queries()` when present.
6. Add plugin template paths to the Jinja loader before the built-in package
   templates.
7. Load built-in filters.
8. Load non-conflicting plugin filters.
9. Collect non-conflicting plugin queries.

Because plugin template paths are loaded before the built-in template package, a
plugin can add completely new template paths or intentionally shadow a built-in
template path. Shadowing is powerful and should be rare, explicit, and covered
by render tests. Prefer namespaced templates and `extends` when the goal is to
reuse built-in behavior with a small override.

### Plugin Templates

A plugin template path is a root directory with the same logical shape as the
built-in template tree:

```text
templates/
  <platform>/
    <role>/
      base/
      include/
      <firmware-version>/
        entrypoint/
        include/
```

Plugins can:

- Add new platforms, roles, firmware versions, and entrypoint files.
- Add supplemental rendered files for a role by adding more templates under
  `entrypoint/`.
- Reuse built-in base templates with `extends`.
- Override individual blocks from built-in templates.
- Provide plugin-owned common templates for multiple plugin roles.
- Shadow a built-in template by providing the same logical template path.

Plugins should:

- Namespace plugin-owned common templates.
- Keep role and firmware-specific deltas small.
- Inherit from built-in templates instead of copying them.
- Include render fixtures for every plugin role and entrypoint.
- Avoid relying on relative load order between multiple plugins that provide the
  same template path.

### Plugin Filters

`get_custom_filters()` returns a dictionary mapping Jinja filter names to Python
callables:

```python
from inspect import getmembers, isfunction
from typing import Any

from my_template_plugin.filters import device, location

FILTER_MODULES = [device, location]


def get_custom_filters() -> dict[str, Any]:
    filters: dict[str, Any] = {}
    for filter_module in FILTER_MODULES:
        for name, func in getmembers(filter_module, isfunction):
            if not name.startswith("_") and func.__module__ == filter_module.__name__:
                filters[name] = func
    return filters
```

Plugins use filters to expose plugin-specific domain concepts to templates. A
plugin filter can interpret core `device_data`, core `location_data`, or
plugin-provided query results. This is the correct place to hide plugin model
shape, Nautobot schema details, migration fallback behavior, and output sorting.

Filter naming should be specific enough to avoid collisions. If a plugin filter
name conflicts with an existing built-in filter or a previously loaded plugin
filter, the renderer skips it and logs a warning.

### Plugin GraphQL Queries

`get_graphql_queries()` returns a dictionary of query names to GraphQL query
strings:

```python
def get_graphql_queries() -> dict[str, str]:
    return {
        "my_extra_data": """
        query MyExtraData($id: ID!, $hostname: String) {
          # plugin-owned fields here
        }
        """,
    }
```

The renderer executes every registered plugin query during `load_data()`. It
passes common variables when they are available:

```text
id       # Nautobot device ID
hostname # device hostname
```

Each result is stored under `plugin_data[query_name]` and passed into the Jinja
context. If a plugin query fails, the renderer logs a warning and stores `None`
for that query name so the failure is visible and deterministic.

Query names must be unique across loaded plugins. Later conflicts are skipped
with a warning.

Use plugin queries for data that is plugin-owned or not appropriate for the
core device/location queries. Do not use plugin queries as a reason to put raw
GraphQL response traversal in templates. Add plugin filters that turn
`plugin_data` into stable template concepts.

The CLI can cache plugin query results with `cache-query --output-plugin-file`
and reuse them during local renders with `render --cached-plugin-data`.

### Plugin Location Resolution

A plugin may provide:

```python
from typing import Any


def get_location_name(device_data: dict[str, Any]) -> str | None:
    ...
```

When present, the renderer calls this hook before the built-in `site_name`
filter. Return a location name when the plugin owns a special device-to-location
mapping; return `None` to let the built-in site resolver handle the device.

This hook is useful for templates whose location data should be keyed from a
plugin-specific relationship rather than the normal device site hierarchy.

### Plugin Packaging and Deployment

A plugin package should depend on `nv-config-manager-templates` and publish a
wheel. The render service installs plugin wheels into the render environment so
their entry points are visible to `importlib.metadata`.

The Helm chart can install plugins from images that provide wheel files under:

```text
/plugin-wheels
```

The main render image still provides the template engine and runtime
dependencies. Plugin images should contain plugin wheels and should not vendor a
second copy of the engine unless the deployment contract changes.

Template version reporting includes the engine package version and installed
template plugin package versions. This creates a compound version key like:

```text
engine=nv-config-manager-templates:<engine-version>;plugins=<plugin>:<plugin-version>
```

That version vector lets rendered configuration be compared against the exact
engine and plugin set that produced it.

### Plugin Capability Summary

Plugins can:

- Add new template trees for new platforms, roles, and firmware versions.
- Add additional rendered entrypoint files for matching devices.
- Inherit from built-in templates and override selected blocks.
- Intentionally shadow built-in templates by providing the same logical path.
- Export custom Jinja filters.
- Register additional GraphQL queries.
- Interpret plugin query data through filters.
- Override device-to-location resolution with `get_location_name()`.
- Participate in rendered template version keys through package metadata.
- Ship independently as Python wheels and plugin images.

Plugins should not:

- Put GraphQL queries or Nautobot client calls in Jinja templates.
- Hard-code raw GraphQL response paths in templates.
- Copy large built-in templates for small changes.
- Depend on overriding built-in filters.
- Depend on unspecified load order between multiple plugins with the same
  template paths, filter names, or query names.
- Hide required data failures by rendering incomplete configuration.

## Local Development

Run commands from this directory:

```bash
cd components/network-templates
uv sync
uv run pytest
uv run ruff check src tests
```

Render a cached fixture locally:

```bash
uv run template-cli render \
  --cached-data tests/resources/nautobot/a09-u28-p01-bleaf-01.json \
  --cached-location-data tests/resources/nautobot/TEST-SITE.json \
  --entrypoint startup.yaml.j2
```

Cache data from Nautobot for local iteration:

```bash
uv run template-cli cache-query \
  --hostname <hostname> \
  --nautobot-url <url> \
  --token-file <token-file> \
  --output-file tests/resources/nautobot/<hostname>.json \
  --output-location-file tests/resources/nautobot/<site>.json \
  --output-plugin-file tests/resources/nautobot/<hostname>-plugin-data.json
```

Vault lookups are disabled by default for local renders unless `--vault` is
provided.
