#  SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#  SPDX-License-Identifier: Apache-2.0
#
#  Licensed under the Apache License, Version 2.0 (the "License")
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Tasks for use with Invoke."""

import os
import re
import sys
from pathlib import Path
from time import sleep

from dotenv import load_dotenv
from invoke.collection import Collection
from invoke.exceptions import Exit, UnexpectedExit
from invoke.tasks import task as invoke_task

# These values will be overridden by env vars if they are set.
DEFAULT_NAUTOBOT_VER = "2.4.5"  # NAUTOBOT_VER
DEFAULT_PYTHON_VER = "3.11"  # PYTHON_VER


def load_env_files() -> bool:
    """Load environment files if they exist."""
    if Path("development/development.env").exists():
        load_dotenv("development/development.env")
        print("Loaded env vars from development/development.env")
    if Path("development/creds.env").exists():
        load_dotenv("development/creds.env")
        print("Loaded env vars from development/creds.env")
    else:
        print(
            "Warning: No development/creds.env file found. Run `cp development/creds.example.env development/creds.env` to create one."
        )
    return True


def activate_venv(venv_path: Path) -> bool:
    """Activate a virtual environment for the current process."""
    try:
        activate_this = venv_path / "bin" / "activate_this.py"
        if activate_this.exists():
            with activate_this.open() as f:
                exec(f.read(), {"__file__": str(activate_this)})  # noqa: S102
            return True
    except Exception:
        return False
    return False


# Try to use venv if available
venv = Path(".venv")
if venv and activate_venv(venv):
    if load_env_files():
        print(f"Using python-dotenv from virtual environment at {venv}")
    else:
        print("Warning: python-dotenv not available in virtual environment")
else:
    print("Warning: No venv found or couldn't activate it, trying system Python")
    print("Recommend running `uv sync --frozen` to create a virtual environment and install dependencies.")
    if load_env_files():
        print("Using python-dotenv from system Python")
    else:
        print("Warning: python-dotenv not available in system Python")


def is_truthy(arg):
    """Convert "truthy" strings into Booleans.

    Examples:
        >>> is_truthy('yes')
        True
    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.
    """
    if isinstance(arg, bool):
        return arg

    val = str(arg).lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"Invalid truthy value: `{arg}`")


os.environ.setdefault("NAUTOBOT_VER", DEFAULT_NAUTOBOT_VER)
os.environ.setdefault("PYTHON_VER", DEFAULT_PYTHON_VER)

# Use pyinvoke configuration for default values, see http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Variables may be overwritten in invoke.yml or by the environment variables INVOKE_nautobot_app_overlays_xxx
namespace = Collection("nautobot_app_overlays")
namespace.configure(
    {
        "nautobot_app_overlays": {
            # We don't need to set defaults here because they are set above with os.environ.setdefault
            "nautobot_ver": os.getenv("NAUTOBOT_VER"),
            "python_ver": os.getenv("PYTHON_VER"),
            "project_name": "nautobot-fabric-partitions",
            "local": is_truthy(os.getenv("INVOKE_CONTEXT_LOCAL", False)),
            "compose_dir": os.path.join(os.path.dirname(__file__), "development"),
            "compose_files": [
                "docker-compose.base.yml",
                "docker-compose.redis.yml",
                "docker-compose.postgres.yml",
                "docker-compose.dev.yml",
            ],
            "compose_http_timeout": "86400",
        }
    }
)


def _is_compose_included(context, name):
    return f"docker-compose.{name}.yml" in context.nautobot_app_overlays.compose_files


def _await_healthy_service(context, service):
    container_id = docker_compose(context, f"ps -q -- {service}", pty=False, echo=False, hide=True).stdout.strip()
    _await_healthy_container(context, container_id)


def _await_healthy_container(context, container_id):
    while True:
        result = context.run(
            "docker inspect --format='{{.State.Health.Status}}' " + container_id,
            pty=False,
            echo=False,
            hide=True,
        )
        if result.stdout.strip() == "healthy":
            break
        print(f"Waiting for `{container_id}` container to become healthy ...")
        sleep(1)


def task(function=None, *args, **kwargs):
    """Task decorator to override the default Invoke task decorator and add each task to the invoke namespace."""

    def task_wrapper(function=None):
        """Wrapper around invoke.task to add the task to the namespace as well."""
        if args or kwargs:
            task_func = invoke_task(*args, **kwargs)(function)
        else:
            task_func = invoke_task(function)
        namespace.add_task(task_func)
        return task_func

    if function:
        # The decorator was called with no arguments
        return task_wrapper(function)
    # The decorator was called with arguments
    return task_wrapper


def docker_compose(context, command, **kwargs):
    """Helper function for running a specific docker compose command with all appropriate parameters and environment.

    Args:
        context (obj): Used to run specific commands
        command (str): Command string to append to the "docker compose ..." command, such as "build", "up", etc.
        **kwargs: Passed through to the context.run() call.
    """
    build_env = {
        # Note: 'docker compose logs' will stop following after 60 seconds by default,
        # so we are overriding that by setting this environment variable.
        "COMPOSE_HTTP_TIMEOUT": context.nautobot_app_overlays.compose_http_timeout,
        "NAUTOBOT_VER": context.nautobot_app_overlays.nautobot_ver,
        "PYTHON_VER": context.nautobot_app_overlays.python_ver,
        **kwargs.pop("env", {}),
    }
    compose_command_tokens = [
        "docker compose",
        f"--project-name {context.nautobot_app_overlays.project_name}",
        f'--project-directory "{context.nautobot_app_overlays.compose_dir}"',
    ]

    for compose_file in context.nautobot_app_overlays.compose_files:
        compose_file_path = os.path.join(context.nautobot_app_overlays.compose_dir, compose_file)
        compose_command_tokens.append(f' -f "{compose_file_path}"')

    compose_command_tokens.append(command)

    # If `service` was passed as a kwarg, add it to the end.
    service = kwargs.pop("service", None)
    if service is not None:
        compose_command_tokens.append(service)

    print(f'Running docker compose command "{command}"')
    compose_command = " ".join(compose_command_tokens)

    return context.run(compose_command, env=build_env, **kwargs)


def run_command(context, command, service="nautobot", **kwargs):
    """Wrapper to run a command locally or inside the nautobot container."""
    if is_truthy(context.nautobot_app_overlays.local):
        if "command_env" in kwargs:
            kwargs["env"] = {
                **kwargs.get("env", {}),
                **kwargs.pop("command_env"),
            }
        return context.run(command, **kwargs)
    else:
        # Check if service is running, no need to start another container to run a command
        docker_compose_status = "ps --services --filter status=running"
        results = docker_compose(context, docker_compose_status, hide="out")

        command_env_args = ""
        if "command_env" in kwargs:
            command_env = kwargs.pop("command_env")
            for key, value in command_env.items():
                command_env_args += f' --env="{key}={value}"'

        if service in results.stdout:
            compose_command = f"exec{command_env_args} {service} {command}"
        else:
            compose_command = f"run{command_env_args} --rm --entrypoint='{command}' {service}"

        pty = kwargs.pop("pty", True)

        return docker_compose(context, compose_command, pty=pty, **kwargs)


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task(
    help={
        "force_rm": "Always remove intermediate containers",
        "cache": "Whether to use Docker's cache when building the image (defaults to enabled)",
    }
)
def build(context, force_rm=False, cache=True):
    """Build Nautobot docker image."""
    command = "build"

    if not cache:
        command += " --no-cache"
    if force_rm:
        command += " --force-rm"

    print(f"Building Nautobot with Python {context.nautobot_app_overlays.python_ver}...")
    docker_compose(context, command)


@task
def generate_packages(context):
    """Generate all Python packages inside docker and copy the file locally under dist/."""
    command = "uv build"
    run_command(context, command)


def _get_docker_nautobot_version(context, nautobot_ver=None, python_ver=None):
    """Extract Nautobot version from base docker image."""
    if nautobot_ver is None:
        nautobot_ver = context.nautobot_app_overlays.nautobot_ver
    if python_ver is None:
        python_ver = context.nautobot_app_overlays.python_ver
    dockerfile_path = os.path.join(context.nautobot_app_overlays.compose_dir, "Dockerfile")
    base_image = context.run(f"grep --max-count=1 '^FROM ' {dockerfile_path}", hide=True).stdout.strip().split(" ")[1]
    base_image = base_image.replace(r"${NAUTOBOT_VER}", nautobot_ver).replace(r"${PYTHON_VER}", python_ver)
    pip_nautobot_ver = context.run(f"docker run --rm --entrypoint '' {base_image} pip show nautobot", hide=True)
    match_version = re.search(r"^Version: (.+)$", pip_nautobot_ver.stdout.strip(), flags=re.MULTILINE)
    if match_version:
        return match_version.group(1)
    else:
        raise Exit(f"Nautobot version not found in Docker base image {base_image}.")


@task(
    help={
        "check": (
            "If enabled, check for outdated dependencies in the uv.lock file, "
            "instead of generating a new one. (default: disabled)"
        ),
        "constrain_nautobot_ver": (
            "Run 'uv add nautobot@[version] --lock' to generate the lockfile, "
            "where [version] is the version installed in the Dockerfile's base image. "
            "Generally intended to be used in CI and not for local development. (default: disabled)"
        ),
        "constrain_python_ver": (
            "When using `constrain_nautobot_ver`, further constrain the nautobot version "
            "to python_ver so that uv doesn't complain about python version incompatibilities. "
            "Generally intended to be used in CI and not for local development. (default: disabled)"
        ),
    }
)
def lock(context, check=False, constrain_nautobot_ver=False, constrain_python_ver=False):
    """Generate uv.lock file."""
    if constrain_nautobot_ver:
        docker_nautobot_version = _get_docker_nautobot_version(context)
        command = f"uv add --lock nautobot@{docker_nautobot_version}"
        if constrain_python_ver:
            command += f" --python {context.nautobot_app_overlays.python_ver}"
        try:
            run_command(context, command, hide=True)
            output = run_command(context, command, hide=True)
            print(output.stdout, end="")
            print(output.stderr, file=sys.stderr, end="")
        except UnexpectedExit:
            print("Unable to add Nautobot dependency with version constraint, falling back to git branch.")
            command = f"uv add --lock git+https://github.com/nautobot/nautobot.git#{context.nautobot_app_overlays.nautobot_ver}"
            if constrain_python_ver:
                command += f" --python {context.nautobot_app_overlays.python_ver}"
            run_command(context, command)
    else:
        command = f"uv lock {'--check' if check else '--no-upgrade'}"
        run_command(context, command)


# ------------------------------------------------------------------------------
# START / STOP / DEBUG
# ------------------------------------------------------------------------------
@task(help={"service": "If specified, only affect this service."})
def debug(context, service=""):
    """Start specified or all services and its dependencies in debug mode."""
    print(f"Starting {service} in debug mode...")
    docker_compose(context, "up", service=service)


@task(help={"service": "If specified, only affect this service."})
def start(context, service=""):
    """Start specified or all services and its dependencies in detached mode."""
    print("Starting Nautobot in detached mode...")
    docker_compose(context, "up --detach", service=service)


@task(help={"service": "If specified, only affect this service."})
def restart(context, service=""):
    """Gracefully restart specified or all services."""
    print("Restarting Nautobot...")
    docker_compose(context, "restart", service=service)


@task(help={"service": "If specified, only affect this service."})
def stop(context, service=""):
    """Stop specified or all services, if service is not specified, remove all containers."""
    print("Stopping Nautobot...")
    docker_compose(context, "stop" if service else "down --remove-orphans", service=service)


@task(
    aliases=("down",),
    help={
        "volumes": "Remove Docker compose volumes (default: True)",
    },
)
def destroy(context, volumes=True):
    """Destroy all containers and volumes."""
    print("Destroying Nautobot...")
    docker_compose(context, f"down --remove-orphans {'--volumes' if volumes else ''}")


@task
def export(context):
    """Export docker compose configuration to `compose.yaml` file.

    Useful to:

    - Debug docker compose configuration.
    - Allow using `docker compose` command directly without invoke.
    """
    docker_compose(context, "convert > compose.yaml")


@task(name="ps", help={"all": "Show all, including stopped containers"})
def ps_task(context, all=False):
    """List containers."""
    docker_compose(context, f"ps {'--all' if all else ''}")


@task(
    help={
        "service": "If specified, only display logs for this service (default: all)",
        "follow": "Flag to follow logs (default: False)",
        "tail": "Tail N number of lines (default: all)",
    }
)
def logs(context, service="", follow=False, tail=0):
    """View the logs of a docker compose service."""
    command = "logs "

    if follow:
        command += "--follow "
    if tail:
        command += f"--tail={tail} "

    docker_compose(context, command, service=service)


# ------------------------------------------------------------------------------
# ACTIONS
# ------------------------------------------------------------------------------
@task(
    help={
        "file": "Python file to execute",
        "env": "Environment variables to pass to the command",
        "plain": "Flag to run nbshell in plain mode (default: False)",
    },
)
def nbshell(context, file="", env={}, plain=False):
    """Launch an interactive nbshell session."""
    command = [
        "nautobot-server",
        "nbshell",
        "--plain" if plain else "",
        f"< '{file}'" if file else "",
    ]
    run_command(context, " ".join(command), pty=not bool(file), command_env=env)


@task
def shell_plus(context):
    """Launch an interactive shell_plus session."""
    command = "nautobot-server shell_plus"
    run_command(context, command)


@task(
    help={
        "service": "Docker compose service name to launch cli in (default: nautobot).",
    }
)
def cli(context, service="nautobot"):
    """Launch a bash shell inside the container."""
    run_command(context, "bash", service=service)


@task(
    help={
        "user": "name of the superuser to create (default: admin)",
    }
)
def createsuperuser(context, user="admin"):
    """Create a new Nautobot superuser account (default: "admin"), will prompt for password."""
    command = f"nautobot-server createsuperuser --username {user}"

    run_command(context, command)


@task(
    help={
        "name": "name of the migration to be created; if unspecified, will autogenerate a name",
    }
)
def makemigrations(context, name=""):
    """Perform makemigrations operation in Django."""
    command = "nautobot-server makemigrations nautobot_app_overlays"

    if name:
        command += f" --name {name}"

    run_command(context, command)


@task
def migrate(context):
    """Perform migrate operation in Django."""
    command = "nautobot-server migrate"

    run_command(context, command)


@task(help={})
def post_upgrade(context):
    """
    Performs Nautobot common post-upgrade operations using a single entrypoint.

    This will run the following management commands with default settings, in order:

    - migrate
    - trace_paths
    - collectstatic
    - remove_stale_contenttypes
    - clearsessions
    - invalidate all
    """
    command = "nautobot-server post_upgrade"

    run_command(context, command)


@task(
    help={
        "flush": "Delete all existing Overlays data before populating (default: False)",
    }
)
def populate(context, flush=False):
    """Populate sample Overlays data for development and testing.

    Creates sample overlays, VXLANs, InfiniBand PKeys, MKeys, and overlay assignments.
    Use --flush to delete existing data first.
    """
    command = "nautobot-server populate_overlays"
    if flush:
        command += " --flush"

    run_command(context, command)


# ------------------------------------------------------------------------------
# DOCS
# ------------------------------------------------------------------------------
@task
def docs(context):
    """Build and serve docs locally for development."""
    command = "mkdocs serve -v"

    if is_truthy(context.nautobot_app_overlays.local):
        print(">>> Serving Documentation at http://localhost:8001")
        run_command(context, command)
    else:
        start(context, service="docs")


@task
def build_and_check_docs(context):
    """Build documentation to be available within Nautobot."""
    command = "mkdocs build --no-directory-urls --strict"
    run_command(context, command)


@task(name="help")
def help_task(context):
    """Print the help of available tasks."""
    root = Collection.from_module(sys.modules[__name__])
    for task_name in sorted(root.task_names):
        print(50 * "-")
        print(f"invoke {task_name} --help")
        context.run(f"invoke {task_name} --help")


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------
@task
def pylint(context):
    """Run pylint code analysis."""
    exit_code = 0

    base_pylint_command = 'pylint --verbose --init-hook "import nautobot; nautobot.setup()" --rcfile pyproject.toml'
    command = f"{base_pylint_command} nautobot_app_overlays"
    if not run_command(context, command, warn=True):
        exit_code = 1

    # run the pylint_django migrations checkers on the migrations directory, if one exists
    migrations_dir = Path(__file__).absolute().parent / Path("nautobot_app_overlays") / Path("migrations")
    if migrations_dir.is_dir():
        migrations_pylint_command = (
            f"{base_pylint_command} --load-plugins=pylint_django.checkers.migrations"
            " --disable=all --enable=fatal,new-db-field-with-default,missing-backwards-migration-callable"
            " nautobot_app_overlays.migrations"
        )
        if not run_command(context, migrations_pylint_command, warn=True):
            exit_code = 1
    else:
        print("No migrations directory found, skipping migrations checks.")

    if exit_code != 0:
        raise Exit(code=exit_code)


@task(aliases=("a",))
def autoformat(context):
    """Run code autoformatting."""
    ruff(context, action=["format"], fix=True)


@task(
    help={
        "action": "Available values are `['lint', 'format']`. Can be used multiple times. (default: `['lint', 'format']`)",
        "target": "File or directory to inspect, repeatable (default: all files in the project will be inspected)",
        "fix": "Automatically fix selected actions. May not be able to fix all issues found. (default: False)",
        "output_format": "See https://docs.astral.sh/ruff/settings/#output-format for details. (default: `concise`)",
    },
    iterable=["action", "target"],
)
def ruff(context, action=None, target=None, fix=False, output_format="concise"):
    """Run ruff to perform code formatting and/or linting."""
    if not action:
        action = ["lint", "format"]
    if not target:
        target = ["."]

    exit_code = 0

    if "format" in action:
        command = "ruff format "
        if not fix:
            command += "--check "
        command += " ".join(target)
        if not run_command(context, command, warn=True):
            exit_code = 1

    if "lint" in action:
        command = "ruff check "
        if fix:
            command += "--fix "
        command += f"--output-format {output_format} "
        command += " ".join(target)
        if not run_command(context, command, warn=True):
            exit_code = 1

    if exit_code != 0:
        raise Exit(code=exit_code)


@task
def yamllint(context):
    """Run yamllint to validate formatting adheres to NTC defined YAML standards.

    Args:
        context (obj): Used to run specific commands
    """
    command = "yamllint . --format standard"
    run_command(context, command)


@task
def check_migrations(context):
    """Check for missing migrations."""
    command = "nautobot-server makemigrations --dry-run --check"

    run_command(context, command)


@task(
    help={
        "keepdb": "save and re-use test database between test runs for faster re-testing.",
        "label": "specify a directory or module to test instead of running all Nautobot tests",
        "failfast": "fail as soon as a single test fails don't run the entire test suite",
        "buffer": "Discard output from passing tests",
        "pattern": "Run specific test methods, classes, or modules instead of all tests",
        "verbose": "Enable verbose test output.",
        "coverage": "Enable coverage reporting. Defaults to False",
    }
)
def unittest(  # noqa: PLR0913
    context,
    keepdb=False,
    label="nautobot_app_overlays",
    failfast=False,
    buffer=True,
    pattern="",
    verbose=False,
    coverage=False,
):
    """Run Nautobot unit tests."""
    if coverage:
        command = f"coverage run --module nautobot.core.cli test {label}"
    else:
        command = f"nautobot-server test {label}"

    if keepdb:
        command += " --keepdb"
    if failfast:
        command += " --failfast"
    if buffer:
        command += " --buffer"
    if pattern:
        command += f" -k='{pattern}'"
    if verbose:
        command += " --verbosity 2"

    run_command(context, command)


@task
def unittest_coverage(context):
    """Report on code test coverage as measured by 'invoke unittest --coverage'."""
    command = "coverage report --skip-covered --include 'nautobot_app_overlays/*' --omit *migrations*"

    run_command(context, command)


@task(
    help={
        "failfast": "fail as soon as a single test fails don't run the entire test suite. (default: False)",
        "keepdb": "Save and re-use test database between test runs for faster re-testing. (default: False)",
        "lint-only": "Only run linters; unit tests will be excluded. (default: False)",
        "fix": "Automatically fix fixable linting errors. (default: False)",
    }
)
def tests(context, failfast=False, keepdb=False, lint_only=False, fix=False):
    """Run all tests for this app."""
    # If we are not running locally, start the docker containers so we don't have to for each test
    # If we are running in CI, we don't need to start the docker containers as they are already running
    if not is_truthy(context.nautobot_app_overlays.local):
        print("Starting Docker Containers...")
        start(context)
    # Sorted loosely from fastest to slowest
    print("Running ruff...")
    ruff(context, fix=fix)
    print("Running yamllint...")
    yamllint(context)
    print("Running uv lock...")
    lock(context, check=True)
    print("Running migrations check...")
    check_migrations(context)
    if not lint_only:
        print("Running unit tests...")
        unittest(context, failfast=failfast, keepdb=keepdb, coverage=True)
        unittest_coverage(context)
    print("All tests have passed!")
