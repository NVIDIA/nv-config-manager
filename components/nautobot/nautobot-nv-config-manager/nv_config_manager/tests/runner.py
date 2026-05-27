#  SPDX-FileCopyrightText: Copyright (c) "2025" NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
"""Test runner wrapper to enable xUnit reporting."""

from django.conf import settings
from django.core.management import call_command
from xmlrunner.extra.djangotestrunner import XMLTestRunner


class PluginTestRunner(XMLTestRunner):
    """Version of the NautobotTestRunner that doesn't flush the database by default."""

    exclude_tags = ["integration"]

    def __init__(self, cache_test_fixtures=False, **kwargs):
        """Handle the test arguments and initialize the runner."""
        self.cache_test_fixtures = cache_test_fixtures
        self.fixture_file = kwargs.get("fixture_file", "development/factory_dump.json")
        self.report_file = kwargs.get("report_file")
        self.generate_test_data = kwargs.get("generate_test_data", False)
        self.seed = kwargs.get("seed")

        # Assert "integration" hasn't been provided w/ --tag
        incoming_tags = kwargs.get("tags") or []
        # Assert "exclude_tags" hasn't been provided w/ --exclude-tag; else default to our own.
        incoming_exclude_tags = kwargs.get("exclude_tags") or []

        # Only include our excluded tags if "integration" isn't provided w/ --tag
        if "integration" not in incoming_tags:
            incoming_exclude_tags.append("integration")
            kwargs["exclude_tags"] = incoming_exclude_tags

        super().__init__(**kwargs)

    @classmethod
    def add_arguments(cls, parser):
        """Add the extra arguments that would come from NautobotTestRunner, and reporting args."""
        super().add_arguments(parser)
        parser.add_argument(
            "--cache-test-fixtures",
            action="store_true",
            help="Save test database to a json fixture file to re-use on subsequent tests.",
        )
        parser.add_argument(
            "--fixture-file",
            default="development/factory_dump.json",
            help="Fixture file to use with --cache-test-fixtures.",
        )
        parser.add_argument(
            "--report-file",
            default="rspec.xml",
            help="Filename for the saved XML test report.",
        )
        parser.add_argument(
            "-G",
            "--generate-test-data",
            action="store_true",
            help="Generate a default set of test data and populate the testing database. "
            "Equivalent to the TEST_USE_FACTORIES setting.",
        )
        parser.add_argument(
            "--seed",
            action="store_true",
            help="String to use as a random generator seed for reproducible results. "
            "Equivalent to the TEST_FACTORY_SEED setting.",
        )

    def setup_test_environment(self, **kwargs):
        """Adjust test environment settings based on command-line options."""
        super().setup_test_environment(**kwargs)

        # Remove 'testserver' that Django "helpfully" adds automatically
        # to ALLOWED_HOSTS, masking issues like #3065
        settings.ALLOWED_HOSTS.remove("testserver")

        # Update the XMLTestRunner settings if needed.
        settings.TEST_OUTPUT_VERBOSE = self.verbosity
        if self.report_file is not None:
            settings.TEST_OUTPUT_FILE_NAME = self.report_file

        # Update test factory options
        if self.generate_test_data and not settings.TEST_USE_FACTORIES:
            settings.TEST_USE_FACTORIES = True
            if self.seed:
                settings.TEST_FACTORY_SEED = self.seed

    def setup_databases(self, **kwargs):
        """Set up a standalone database for testing."""
        result = super().setup_databases(**kwargs)

        if settings.TEST_USE_FACTORIES and result:
            command = ["create_env", "--flush", "--no-input"]
            if settings.TEST_FACTORY_SEED is not None:
                command += ["--seed", settings.TEST_FACTORY_SEED]
            if self.cache_test_fixtures:
                command += ["--cache-test-fixtures"]
            if self.fixture_file:
                command.extend(["--fixture-file", self.fixture_file])

            for connection in result:
                db_name = connection[0].alias
                print(f'Pre-populating test database "{db_name}"...')
                db_command = command + ["--database", db_name]
                call_command(*db_command)

        return result

    def teardown_databases(self, old_config, **kwargs):
        """Clean out the test database after the suite has run."""
        if settings.TEST_USE_FACTORIES and old_config:
            command = ["flush_env", "--no-input"]
            for connection in old_config:
                db_name = connection[0].alias
                print(f"Cleaning up test database {db_name}...")
                db_command = command + ["--database", db_name]
                call_command(*db_command)
                print(f"Database {db_name} emptied!")

        super().teardown_databases(old_config, **kwargs)
