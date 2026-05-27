# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""CLI commands for local template iteration."""

# pylint: disable=too-many-arguments
import json
import os
import sys

import click

from nv_config_manager_templates.render import Renderer


def _init_renderer(
    token_file: str = None,
    nautobot_url: str = None,
    token: str = None,
) -> Renderer:
    """Initialize renderer with nautobot credentials.

    Args:
        token_file: Path to file containing token (mutually exclusive with token)
        nautobot_url: Direct Nautobot URL
        token: Direct token value (mutually exclusive with token_file)
    """
    if token_file and token:
        raise click.ClickException("--token-file and --token are mutually exclusive")

    if not nautobot_url:
        raise click.ClickException("Must provide --nautobot-url")

    # Determine token
    if token:
        token_value = token
    elif token_file:
        with open(token_file, encoding="utf-8") as f:
            token_value = f.read().rstrip()
    else:
        raise click.ClickException("Must provide either --token-file or --token")

    return Renderer(nautobot_url=nautobot_url, nautobot_token=token_value)


def _exception_handler(exception_type, exception, traceback):  # pylint: disable=unused-argument
    print(f"{exception_type.__name__}: {exception} Use --debug for more detail.")


@click.group()
def cli():
    """Template CLI operations."""


@cli.command()
@click.option("--hostname", help="nautobot device hostname")
@click.option("--device-id", help="nautobot device ID")
@click.option("--nautobot-url", help="nautobot URL")
@click.option("--token-file", help="file containing your nautobot token")
@click.option("--token", help="nautobot token (mutually exclusive with --token-file)")
@click.option("--cached-data", help="cache of device graphql query data to use for render")
@click.option("--debug", is_flag=True, default=False, help="display tracebacks in error output.")
def list_entrypoints(
    hostname: str,
    device_id: str,
    nautobot_url: str,
    token_file: str,
    token: str,
    cached_data: str,
    debug: bool,
):
    """List entrypoint templates for a given device."""
    if not debug:
        sys.excepthook = _exception_handler
    if cached_data:
        # If using cached data, no need for valid nautobot parameters
        with open(cached_data, encoding="utf-8") as f:
            device_data = json.load(f)
        renderer = Renderer(None, None)
    else:
        renderer = _init_renderer(
            token_file=token_file,
            nautobot_url=nautobot_url,
            token=token,
        )
        device_data = renderer.nautobot_client.load_device_data(
            device_id=device_id, hostname=hostname
        )

    print("Templates:")
    for template in renderer.list_entrypoints(device_data):
        print(f"\t{template}")


@cli.command()
@click.option("--hostname", help="nautobot device hostname")
@click.option("--device-id", help="nautobot device ID")
@click.option("--nautobot-url", help="nautobot URL")
@click.option("--token-file", help="file containing your nautobot token")
@click.option("--token", help="nautobot token (mutually exclusive with --token-file)")
@click.option("--cached-data", help="cache of device graphql query data to use for render")
@click.option(
    "--cached-location-data",
    help="cache of location graphql query data to use for render",
)
@click.option(
    "--cached-plugin-data",
    help="cache of plugin graphql query data to use for render",
)
@click.option("--entrypoint", help="entrypoint template to render")
@click.option("--template", help="full template path to render")
@click.option("--output-file", help="optional output file for rendered output")
@click.option("--vault", is_flag=True, default=False, help="Perform vault lookups during render.")
@click.option("--debug", is_flag=True, default=False, help="display tracebacks in error output.")
def render(  # pylint: disable=too-many-arguments, too-many-locals, too-many-branches
    hostname: str,
    device_id: str,
    nautobot_url: str,
    token_file: str,
    token: str,
    cached_data: str,
    cached_location_data: str,
    cached_plugin_data: str,
    entrypoint: str,
    template: str,
    output_file: str,
    vault: bool,
    debug: bool,
):
    """Render a template for a given device."""
    if not debug:
        sys.excepthook = _exception_handler

    if not vault:
        # Disable vault lookups unless requested.
        os.environ["NV_CONFIG_MANAGER_SKIP_VAULT"] = "1"
        os.environ["NV_CONFIG_MANAGER_DEV_SALT"] = "H0QFj2rx"
        os.environ["NV_CONFIG_MANAGER_DEV_SALT_T7"] = "0"

    if not (template or entrypoint):
        raise click.ClickException("Must supply either an entrypoint or full template path.")

    if cached_data and cached_location_data:
        # If using cached data, no need for valid nautobot parameters
        renderer = Renderer(None, None)
    else:
        renderer = _init_renderer(
            token_file=token_file,
            nautobot_url=nautobot_url,
            token=token,
        )

    device_data = None
    if cached_data:
        with open(cached_data, encoding="utf-8") as f:
            device_data = json.load(f)

    location_data = None
    if cached_location_data:
        with open(cached_location_data, encoding="utf-8") as f:
            location_data = json.load(f)

    # Load cached plugin data if provided
    cached_plugin_data_dict = None
    if cached_plugin_data:
        with open(cached_plugin_data, encoding="utf-8") as f:
            cached_plugin_data_dict = json.load(f)

    device_data, location_data, plugin_data = renderer.load_data(
        device_id=device_id,
        hostname=hostname,
        device_data=device_data,
        location_data=location_data,
    )

    # Use cached plugin data if provided, otherwise use freshly loaded
    if cached_plugin_data_dict is not None:
        plugin_data = cached_plugin_data_dict

    if template is None:
        try:
            template = next(
                template
                for template in renderer.list_entrypoints(device_data)
                if template.endswith(f"/{entrypoint}")
            )
        except StopIteration as exc:
            raise click.ClickException(
                f"No entrypoint template found with name {entrypoint}"
            ) from exc

    output = renderer.render(template, device_data, location_data, plugin_data)
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        print(output)


@cli.command()
@click.option("--hostname", help="nautobot device hostname")
@click.option("--device-id", help="nautobot device ID")
@click.option("--nautobot-url", help="nautobot URL", required=True)
@click.option("--token-file", help="file containing your nautobot token")
@click.option("--token", help="nautobot token (mutually exclusive with --token-file)")
@click.option(
    "--output-file",
    help="file in which to cache nautobot device query data",
    required=True,
)
@click.option(
    "--output-location-file",
    help="file in which to cache nautobot location query data",
    required=True,
)
@click.option(
    "--output-plugin-file",
    help="optional file in which to cache plugin query data",
)
@click.option("--debug", is_flag=True, default=False, help="display tracebacks in error output.")
def cache_query(
    hostname: str,
    device_id: str,
    nautobot_url: str,
    token_file: str,
    token: str,
    output_file: str,
    output_location_file: str,
    output_plugin_file: str,
    debug: bool,
):
    """Cache GraphQL query data for a given device."""
    if not debug:
        sys.excepthook = _exception_handler
    renderer = _init_renderer(
        token_file=token_file,
        nautobot_url=nautobot_url,
        token=token,
    )
    print("Querying nautobot for device and location data.")
    device_data, location_data, plugin_data = renderer.load_data(device_id, hostname)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(device_data, f, indent=4)
    with open(output_location_file, "w", encoding="utf-8") as f:
        json.dump(location_data, f, indent=4)

    # Cache plugin data if provided and output file specified
    if plugin_data:
        if output_plugin_file:
            with open(output_plugin_file, "w", encoding="utf-8") as f:
                json.dump(plugin_data, f, indent=4)
            print(f"Plugin data ({len(plugin_data)} quer(ies)) cached to {output_plugin_file}.")
        else:
            print(
                f"Note: {len(plugin_data)} plugin quer(ies) were executed but "
                f"not cached. Use --output-plugin-file to cache."
            )

    print(
        f"Device data has been cached to {output_file}, "
        f"location data has been cached to {output_location_file}."
    )


def main():
    """CLI entrypoint."""
    cli()


if __name__ == "__main__":
    sys.exit(main())
