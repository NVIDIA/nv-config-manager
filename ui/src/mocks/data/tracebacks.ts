/*
 * SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
export const TRACEBACKS = {
  simple_value_error:
    'Traceback (most recent call last):\n  File "/app/main.py", line 45, in process_data\n    result = calculate_value(user_input)\n  File "/app/calculator.py", line 23, in calculate_value\n    return 100 / int(value)\nValueError: invalid literal for int() with base 10: \'abc\'',

  division_by_zero:
    'Traceback (most recent call last):\n  File "/app/main.py", line 45, in process_data\n    result = calculate_value(user_input)\n  File "/app/calculator.py", line 23, in calculate_value\n    return 100 / int(value)\n    ^^^^^^^^^^^^^^^^^^^^^^\nZeroDivisionError: division by zero',

  nested_exception:
    'Traceback (most recent call last):\n  File "/app/api/routes.py", line 28, in get_user_data\n    data = fetch_user(user_id)\n  File "/app/services/user_service.py", line 45, in fetch_user\n    response = make_db_request(query)\n  File "/app/db/connector.py", line 67, in make_db_request\n    conn = get_connection()\n  File "/app/db/connector.py", line 31, in get_connection\n    raise ConnectionError("Failed to connect to database")\nConnectionError: Failed to connect to database\n\nThe above exception was the direct cause of the following exception:\n\nTraceback (most recent call last):\n  File "/app/server.py", line 102, in handle_request\n    response = router.dispatch(request)\n  File "/app/api/router.py", line 54, in dispatch\n    return route_handler(request)\n  File "/app/api/middleware.py", line 23, in error_handling_middleware\n    raise ServiceUnavailableError("Database connection failed") from e\nServiceUnavailableError: Database connection failed',

  syntax_error:
    'Traceback (most recent call last):\n  File "/app/main.py", line 10, in <module>\n    import custom_module\n  File "/app/custom_module.py", line 15\n    if value = 5:\n          ^\nSyntaxError: invalid syntax',

  complex_multi_level:
    'Traceback (most recent call last):\n  File "/app/scheduler.py", line 87, in run_task\n    task.execute()\n  File "/app/tasks/base.py", line 42, in execute\n    self._validate()\n  File "/app/tasks/email_task.py", line 29, in _validate\n    if not self._is_valid_email(self.recipient):\n  File "/app/tasks/email_task.py", line 53, in _is_valid_email\n    match = re.match(EMAIL_PATTERN, email)\n  File "/usr/lib/python3.9/re.py", line 191, in match\n    return _compile(pattern, flags).match(string)\nTypeError: expected string or bytes-like object, got NoneType\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File "/app/worker.py", line 134, in process_queue\n    result = scheduler.run_task(task)\n  File "/app/scheduler.py", line 92, in run_task\n    self._log_error(task, e)\n  File "/app/scheduler.py", line 105, in _log_error\n    logger.error(f"Task {task.id} failed: {error_details}")\n  File "/app/logger.py", line 67, in error\n    self._write_to_log(message, level="ERROR")\n  File "/app/logger.py", line 112, in _write_to_log\n    with open(self.log_file, \'a\') as f:\nFileNotFoundError: [Errno 2] No such file or directory: \'/var/log/app/errors.log\'',
};
