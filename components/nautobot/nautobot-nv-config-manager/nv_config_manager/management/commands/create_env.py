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
"""Bootstrap dummy data for local testing."""

import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.utils.crypto import get_random_string
from nautobot.users.models import Token

from nv_config_manager.tests.fixtures.create_obj_fixtures import create_env


class Command(BaseCommand):
    """Publish the command to bootstrap dummy data."""

    def add_arguments(self, parser):
        """Optional command-line arguments for the handler."""
        super().add_arguments(parser)
        parser.add_argument(
            "--seed",
            help="String to use as a random generator seed for reproducible results.",
        )
        parser.add_argument(
            "--cache-fixtures",
            action="store_true",
            help="Save the generated test data to a json fixture file to re-use if the fixture "
            "file is not found, load the previously generated test data from the fixture "
            "file if it exists (implies the --flush option).",
        )
        parser.add_argument(
            "--fixture-file",
            default="development/factory_dump.json",
            help="Fixture file to use with --cache-fixtures.",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Flush any existing data in the database before generating new test data.",
        )
        parser.add_argument(
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do NOT prompt the user for input or confirmation of any kind.",
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help='The database to generate the test data in. Defaults to the "default" database.',
        )
        parser.add_argument(
            "--with-demo-objects",
            action="store_true",
            help="Create demo Config Manager objects in the environment. Should be used "
            "for a demo environment, not unit testing.",
        )

    def _create_superuser(self):
        """Create the default superuser account."""
        # After a database flush, the admin account needs to be recreated.
        username = os.environ.get("NAUTOBOT_SUPERUSER_NAME", "admin")
        password = os.environ.get("NAUTOBOT_SUPERUSER_PASSWORD", "admin")
        email = os.environ.get("NAUTOBOT_SUPERUSER_EMAIL", "admin@example.com")
        token = os.environ.get("NAUTOBOT_SUPERUSER_TOKEN", "0123456789abcdef0123456789abcdef01234567")

        admin_user = get_user_model().objects.filter(username=username)
        if not admin_user:
            admin_user = get_user_model().objects.create_superuser(username, email, password)
            Token.objects.create(user=admin_user, key=token)
        else:
            admin_user = admin_user[0]
            if admin_user.email != email:
                admin_user.email = email
            if not admin_user.check_password(password):
                admin_user.set_password(password)
            admin_user.save()
            admin_token = Token.objects.filter(user=admin_user)
            if admin_token:
                admin_token = admin_token[0]
                if admin_token.key != token:
                    admin_token.key = token
                    admin_token.save()

    # Based on the nautobot generate_test_data management command, but we only need
    # Manufacturer, Role, and DeviceType.
    def _generate_test_data(self, seed: str, db_name: str):  # pylint: disable=too-many-locals
        """Generate the test data for the given database."""
        try:
            # pylint: disable=import-outside-toplevel
            import factory.random
            from nautobot.core.factory import BaseModelFactory
            from nautobot.dcim.factory import LocationFactory, LocationTypeFactory
            from nautobot.extras.factory import RoleFactory, StatusFactory, TagFactory
            from nautobot.extras.management import populate_role_choices, populate_status_choices
            from nautobot.extras.utils import TaggableClassesQuery
            from nautobot.ipam.choices import PrefixTypeChoices
            from nautobot.ipam.factory import (
                NamespaceFactory,
                PrefixFactory,
                RIRFactory,
                RouteTargetFactory,
                VLANFactory,
                VLANGroupFactory,
                VRFFactory,
            )
        except ImportError as error:
            raise CommandError("Unable to load data factories.") from error

        self.stdout.write(f'Seeding the pseudo-random number generator with seed "{seed}"')
        factory.random.reseed_random(seed)

        def _create_batch(
            some_factory: type[BaseModelFactory],
            count: int,
            description: str = "",
            **kwargs,
        ) -> None:
            """Create a batch of test data for the given factory."""
            model = some_factory._meta.get_model_class()
            message = [f"Creating {count} {model._meta.verbose_name_plural}"]
            if description:
                message.append(description)
            self.stdout.write(f"{' '.join(message)}...")
            _ = some_factory.create_batch(count, using=db_name, **kwargs)

        # Create generic factory objects
        populate_role_choices(verbosity=0, using=db_name)
        _create_batch(RoleFactory, count=20)
        populate_status_choices(verbosity=0, using=db_name)
        _create_batch(StatusFactory, 10)
        _create_batch(
            TagFactory,
            5,
            description="on all content-types",
            content_types=TaggableClassesQuery().as_queryset(),
        )
        _create_batch(TagFactory, 15, description="on some content-types")
        _create_batch(LocationTypeFactory, 7)  # only 7 unique LocationTypes are
        # hard-coded presently First 7 locations must be created in specific order so subsequent
        # objects have valid parents to reference
        _create_batch(LocationFactory, 7, description="as structure", has_parent=True)
        _create_batch(LocationFactory, 40)
        _create_batch(
            LocationFactory,
            10,
            description="without a parent Location",
            has_parent=False,
        )
        _create_batch(RIRFactory, 9)  # only 9 unique RIR names are hard-coded presently
        _create_batch(RouteTargetFactory, 20)
        _create_batch(NamespaceFactory, 5)
        _create_batch(VRFFactory, 20)
        _create_batch(VLANGroupFactory, 20)
        _create_batch(VLANFactory, 20)
        for i in range(10):
            _create_batch(
                PrefixFactory,
                1,
                description=f"(10.{i}.0.0/16 and descendants)",
                prefix=f"10.{i}.0.0/16",
                type=PrefixTypeChoices.TYPE_CONTAINER,
            )
            _create_batch(
                PrefixFactory,
                1,
                description=f"(2001:db8:0:{i}::/64 and descendants)",
                prefix=f"2001:db8:0:{i}::/64",
                type=PrefixTypeChoices.TYPE_CONTAINER,
            )
        _create_batch(NamespaceFactory, 5, description="without any Prefixes or IPAddresses")

    def handle(self, *args, **options):
        """Command handler method."""
        if options["cache_fixtures"]:
            options["flush"] = True
            options["interactive"] = False

        db_name = connections[options["database"]].settings_dict["NAME"]
        if options["flush"]:
            if options["interactive"]:
                confirmation = input(f"""
You have requested a flush of the database before generating new data. This will
IRREVERSIBLY DESTROY all data in the "{db_name}" database, including all user accounts,
and return each table to an empty state. Are you sure you want to do this?

Type "yes" to continue, or "no" to cancel: """)
                if confirmation.lower() != "yes":
                    self.stdout.write(self.style.ERROR("Canceled."))
                    return

            self.stdout.write(
                self.style.WARNING(f"Flushing all existing data from the {options['database']} database...")
            )
            call_command("flush", "--no-input", "--database", options["database"])
        if options["cache_fixtures"] and os.path.exists(options["fixture_file"]):
            call_command("loaddata", options["fixture_file"])
        else:
            self.stdout.write(self.style.MIGRATE_HEADING("Populating Nautobot factory test data"))
            if not db_name.startswith("test"):
                self._create_superuser()
            seed = options.get("seed", get_random_string(16))
            self._generate_test_data(seed, options["database"])
            create_env(seed, options["with_demo_objects"])

            if options["cache_fixtures"]:
                self.stdout.write(self.style.WARNING(f"Saving test data to file {options['fixture_file']}"))

                call_command(
                    "dumpdata",
                    indent=2,
                    format="json",
                    exclude=["auth.permission"],
                    output=options["fixture_file"],
                )
                self.stdout.write(self.style.SUCCESS(f"Dumped data to  {options['fixture_file']}."))

        self.stdout.write(self.style.SUCCESS(f"Database {options['database']} successfully populated."))
