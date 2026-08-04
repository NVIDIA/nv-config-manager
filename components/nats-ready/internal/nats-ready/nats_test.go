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
package natsready

import (
	"context"
	"testing"
	"time"

	"github.com/nats-io/nats.go/jetstream"
	"github.com/rs/zerolog"
)

type consumerTestJetStream struct {
	jetstream.JetStream
	stream jetstream.Stream
}

func (m *consumerTestJetStream) Stream(context.Context, string) (jetstream.Stream, error) {
	return m.stream, nil
}

type consumerTestStream struct {
	jetstream.Stream
	consumer        jetstream.Consumer
	consumerErr     error
	createdConfig   jetstream.ConsumerConfig
	createCallCount int
}

func (m *consumerTestStream) Consumer(context.Context, string) (jetstream.Consumer, error) {
	return m.consumer, m.consumerErr
}

func (m *consumerTestStream) CreateConsumer(
	_ context.Context, config jetstream.ConsumerConfig,
) (jetstream.Consumer, error) {
	m.createCallCount++
	m.createdConfig = config
	return m.consumer, nil
}

func TestNewConsumerConfig(t *testing.T) {
	target := newConsumerConfig("events", "nv-config-manager-nautobot", "nautobot")
	config := target.config

	if target.stream != "events" || config.Durable != "nv-config-manager-nautobot" {
		t.Fatalf("unexpected consumer target: %#v", target)
	}
	if config.FilterSubject != "nautobot" {
		t.Fatalf("unexpected filter subject: %q", config.FilterSubject)
	}
	if config.DeliverPolicy != jetstream.DeliverNewPolicy {
		t.Fatalf("unexpected deliver policy: %s", config.DeliverPolicy)
	}
	if config.AckPolicy != jetstream.AckExplicitPolicy {
		t.Fatalf("unexpected ack policy: %s", config.AckPolicy)
	}
	if config.AckWait != 360*time.Second || config.MaxDeliver != -1 || len(config.BackOff) != 0 {
		t.Fatalf("unexpected retry contract: %#v", config)
	}
}

func TestNewArchiveConsumerConfig(t *testing.T) {
	target := newArchiveConsumerConfig(
		"events",
		"nv-config-manager-archive",
		"nv-config-manager.workflow.result",
		"nv-config-manager.archive.delivery",
	)
	config := target.config

	if config.DeliverSubject != "nv-config-manager.archive.delivery" {
		t.Fatalf("unexpected delivery subject: %q", config.DeliverSubject)
	}
	if config.DeliverGroup != "nv-config-manager-archive" {
		t.Fatalf("unexpected delivery group: %q", config.DeliverGroup)
	}
}

func TestGetOrCreateConsumerCreatesMissingDurable(t *testing.T) {
	stream := &consumerTestStream{consumerErr: jetstream.ErrConsumerNotFound}
	runner := &natsReady{
		js:  &consumerTestJetStream{stream: stream},
		log: zerolog.Nop(),
	}
	target := newConsumerConfig("nautobot", "nv-config-manager-nautobot", "nautobot")

	if err := runner.getOrCreateConsumer(context.Background(), &target); err != nil {
		t.Fatal(err)
	}
	if stream.createCallCount != 1 {
		t.Fatalf("CreateConsumer called %d times, want 1", stream.createCallCount)
	}
	if stream.createdConfig.Durable != "nv-config-manager-nautobot" {
		t.Fatalf("created wrong durable: %#v", stream.createdConfig)
	}
}

func TestGetOrCreateConsumerLeavesExistingDurableUntouched(t *testing.T) {
	stream := &consumerTestStream{consumer: struct{ jetstream.Consumer }{}}
	runner := &natsReady{
		js:  &consumerTestJetStream{stream: stream},
		log: zerolog.Nop(),
	}
	target := newConsumerConfig("nautobot", "nv-config-manager-nautobot", "nautobot")

	if err := runner.getOrCreateConsumer(context.Background(), &target); err != nil {
		t.Fatal(err)
	}
	if stream.createCallCount != 0 {
		t.Fatalf("CreateConsumer called %d times, want 0", stream.createCallCount)
	}
}
