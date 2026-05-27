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

"""Management command to clear any existing data in the database."""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections


class Command(BaseCommand):
    """Publish command to flush dummy data."""

    def add_arguments(self, parser):
        """Optional command-line arguments for the flush_env command."""
        parser.add_argument(
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do NOT prompt the user for input or confirmation of any kind.",
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help='The database to flush. Defaults to the "default" database.',
        )

    def handle(self, *args, **options):
        """Publish command to flush dummy data."""
        if options["interactive"]:
            db_name = connections[options["database"]].settings_dict["NAME"]
            confirmation = input(f"""
You have requested a flush of the database. This will IRREVERSIBLY DESTROY all data in the
"{db_name}" database, including all user accounts, and return each table to an empty state.
Are you sure you want to do this?

Type "yes" to continue, or "no" to cancel: """)
            if confirmation.lower() != "yes":
                self.stdout.write(self.style.ERROR("Canceled."))
                return

        self.stdout.write(self.style.WARNING(f"Flushing all existing data from the {options['database']} database..."))
        call_command("flush", "--no-input", "--database", options["database"])
