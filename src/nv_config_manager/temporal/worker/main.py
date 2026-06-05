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
"""Hello World Temporal Worker."""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from nv_config_manager.common.log import configure_logging
from nv_config_manager.temporal.converter import get_data_converter
from nv_config_manager.temporal.hello_world.activities import (
    REGISTERED_ACTIVITIES as HELLO_WORLD_REGISTERED_ACTIVITIES,
)
from nv_config_manager.temporal.hello_world.workflows import (
    LOCAL_TEST_WORKFLOWS as HELLO_WORLD_LOCAL_TEST_WORKFLOWS,
    REGISTERED_WORKFLOWS as HELLO_WORLD_REGISTERED_WORKFLOWS,
)
from nv_config_manager.temporal.ngc.activities import (
    REGISTERED_ACTIVITIES as NGC_REGISTERED_ACTIVITIES,
)
from nv_config_manager.temporal.ngc.workflows import (
    REGISTERED_WORKFLOWS as NGC_REGISTERED_WORKFLOWS,
)

configure_logging(service="temporal-worker")


async def main() -> None:
    """Run the temporal worker."""
    temporal_server = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    client = await Client.connect(
        temporal_server,
        namespace="default",
        data_converter=get_data_converter(),
    )

    # Combine activity lists - registered activities are lists of callables
    all_activities = [*NGC_REGISTERED_ACTIVITIES, *HELLO_WORLD_REGISTERED_ACTIVITIES]

    worker = Worker(
        client,
        task_queue="default-task-queue",
        workflows=[
            *NGC_REGISTERED_WORKFLOWS,
            *HELLO_WORLD_REGISTERED_WORKFLOWS,
            *HELLO_WORLD_LOCAL_TEST_WORKFLOWS,
        ],
        activities=all_activities,  # type: ignore[arg-type]
        activity_executor=ThreadPoolExecutor(100),
    )

    await worker.run()


def cli_main() -> None:
    """CLI entrypoint for temporal worker."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
