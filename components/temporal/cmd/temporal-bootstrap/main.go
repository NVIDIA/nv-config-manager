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

// temporal-bootstrap replaces the shell scripts in Temporal's upstream
// admin-tools image. Keeping the orchestration in a static Go binary lets the
// project-owned bootstrap image use a distroless runtime without changing
// setup semantics.
package main

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"net"
	"os"
	"os/exec"
	"strings"
	"time"
)

const (
	defaultRetries = 30
	retryDelay     = 5 * time.Second
)

var commandTimeout = 2 * time.Minute

var searchAttributes = [][2]string{
	{"User", "Keyword"},
	{"DeviceID", "Keyword"},
	{"DeviceRole", "Keyword"},
	{"DeviceName", "Text"},
	{"DevicePlatform", "Keyword"},
	{"Site", "Text"},
	{"ReadRoles", "KeywordList"},
	{"ExecuteRoles", "KeywordList"},
	{"PendingApproval", "Bool"},
	{"FailedStage", "Bool"},
	{"IssueKey", "Keyword"},
}

func main() {
	if len(os.Args) != 2 {
		fatal("usage: temporal-bootstrap <setup-schema|setup-namespace|wait-namespace>")
	}

	var err error
	switch os.Args[1] {
	case "setup-schema":
		err = setupSchema()
	case "setup-namespace":
		err = setupNamespace()
	case "wait-namespace":
		err = waitForNamespace()
	default:
		fatal("unknown command %q", os.Args[1])
	}
	if err != nil {
		fatal("%v", err)
	}
}

func setupSchema() error {
	port := getenv("TEMPORAL_DB_PORT", "5432")
	if err := initializeSchema(
		"temporal",
		getenv("TEMPORAL_DB_HOST", ""),
		getenv("TEMPORAL_DB_USER", ""),
		getenv("TEMPORAL_DB_PASS", ""),
		port,
		"/etc/temporal/schema/postgresql/v12/temporal/versioned",
	); err != nil {
		return err
	}
	return initializeSchema(
		"visibility",
		getenv("VISIBILITY_DB_HOST", ""),
		getenv("VISIBILITY_DB_USER", ""),
		getenv("VISIBILITY_DB_PASS", ""),
		port,
		"/etc/temporal/schema/postgresql/v12/visibility/versioned",
	)
}

func initializeSchema(name, host, user, password, port, directory string) error {
	if host == "" || user == "" || password == "" {
		return fmt.Errorf("%s database credentials are required", name)
	}

	base := []string{
		"--ep", host,
		"--user", user,
		"--password", password,
		"--port", port,
		"--db", databaseName(name),
		"--plugin", "postgres12",
	}
	if output, err := run("/usr/local/bin/temporal-sql-tool", append(base, "setup-schema", "-v", "0.0")...); err != nil {
		if !alreadyExists(output) {
			return fmt.Errorf("initialize %s schema: %w: %s", name, err, output)
		}
		fmt.Printf("%s schema already exists\n", name)
	}
	if output, err := run("/usr/local/bin/temporal-sql-tool", append(base, "update-schema", "-d", directory)...); err != nil {
		return fmt.Errorf("update %s schema: %w: %s", name, err, output)
	}
	return nil
}

func databaseName(name string) string {
	if name == "visibility" {
		return getenv("VISIBILITY_DB_NAME", "temporal_visibility")
	}
	return getenv("TEMPORAL_DB_NAME", "temporal")
}

func setupNamespace() error {
	address := temporalAddress()
	namespace := temporalNamespace()
	if err := waitForAddress(address); err != nil {
		return err
	}

	if err := retry("create namespace "+namespace, func() (bool, error) {
		output, err := temporal(address, "operator", "namespace", "create", "--namespace", namespace, "--retention", "336h")
		if err == nil || alreadyExists(output) {
			return true, nil
		}
		return false, fmt.Errorf("%w: %s", err, output)
	}); err != nil {
		return err
	}

	if err := retry("update namespace "+namespace+" retention", func() (bool, error) {
		output, err := temporal(address, "operator", "namespace", "update", "--namespace", namespace, "--retention", "336h")
		if err == nil {
			return true, nil
		}
		return false, fmt.Errorf("%w: %s", err, output)
	}); err != nil {
		return err
	}

	for _, attribute := range searchAttributes {
		name, kind := attribute[0], attribute[1]
		if err := retry("create search attribute "+name, func() (bool, error) {
			output, err := temporal(address, "operator", "search-attribute", "create", "--name", name, "--type", kind)
			if err == nil || alreadyExists(output) {
				return true, nil
			}
			return false, fmt.Errorf("%w: %s", err, output)
		}); err != nil {
			return err
		}
	}
	return nil
}

func waitForNamespace() error {
	address := temporalAddress()
	namespace := temporalNamespace()
	if err := waitForAddress(address); err != nil {
		return err
	}
	return retry("wait for namespace "+namespace, func() (bool, error) {
		output, err := temporal(address, "operator", "namespace", "describe", "--namespace", namespace)
		if err == nil {
			return true, nil
		}
		return false, fmt.Errorf("%w: %s", err, output)
	})
}

func temporal(address string, arguments ...string) (string, error) {
	return run("/usr/local/bin/temporal", append([]string{"--address", address, "--disable-config-file"}, arguments...)...)
}

func waitForAddress(address string) error {
	for attempt := 1; attempt <= defaultRetries; attempt++ {
		connection, err := net.DialTimeout("tcp", address, retryDelay)
		if err == nil {
			_ = connection.Close()
			return nil
		}
		if attempt == defaultRetries {
			return fmt.Errorf("Temporal frontend %s did not become reachable: %w", address, err)
		}
		fmt.Printf("waiting for Temporal frontend at %s (attempt %d/%d)\n", address, attempt, defaultRetries)
		time.Sleep(retryDelay)
	}
	return errors.New("unreachable")
}

func retry(name string, operation func() (bool, error)) error {
	for attempt := 1; attempt <= defaultRetries; attempt++ {
		complete, err := operation()
		if complete {
			return nil
		}
		if attempt == defaultRetries {
			return fmt.Errorf("%s failed after %d attempts: %w", name, defaultRetries, err)
		}
		fmt.Printf("%s failed (attempt %d/%d): %v\n", name, attempt, defaultRetries, err)
		time.Sleep(retryDelay)
	}
	return errors.New("unreachable")
}

func run(path string, arguments ...string) (string, error) {
	commandContext, cancel := context.WithTimeout(context.Background(), commandTimeout)
	defer cancel()

	command := exec.CommandContext(commandContext, path, arguments...)
	command.Env = append(os.Environ(), "HOME=/tmp")
	var output bytes.Buffer
	command.Stdout = &output
	command.Stderr = &output
	err := command.Run()
	if commandContext.Err() != nil {
		err = fmt.Errorf("command timed out after %s: %w", commandTimeout, commandContext.Err())
	}
	return output.String(), err
}

func temporalAddress() string {
	address := os.Getenv("TEMPORAL_ADDR")
	if address == "" {
		fatal("TEMPORAL_ADDR is required")
	}
	return address
}

func temporalNamespace() string {
	return getenv("TEMPORAL_NAMESPACE", "default")
}

func alreadyExists(output string) bool {
	return strings.Contains(strings.ToLower(output), "already exist")
}

func getenv(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}

func fatal(format string, values ...any) {
	fmt.Fprintf(os.Stderr, "temporal-bootstrap: "+format+"\n", values...)
	os.Exit(1)
}
