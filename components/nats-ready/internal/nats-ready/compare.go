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
	"reflect"
	"time"

	"github.com/nats-io/nats.go/jetstream"
)

const configMismatchMessage = "Config mismatch"

// configsMatch compares two StreamConfig objects to determine if they match
func (n *natsReady) configsMatch(current, expected *jetstream.StreamConfig) bool {
	return n.compareBasicFields(current, expected) &&
		n.compareLimitFields(current, expected) &&
		n.compareTimeFields(current, expected) &&
		n.comparePolicyFields(current, expected) &&
		n.compareAdvancedFields(current, expected)
}

// compareBasicFields compares core identifying fields
func (n *natsReady) compareBasicFields(current, expected *jetstream.StreamConfig) bool {
	if current.Name != expected.Name {
		n.log.Warn().Str("field", "Name").Str("current", current.Name).Str("expected", expected.Name).Msg(configMismatchMessage)
		return false
	}

	if !reflect.DeepEqual(current.Subjects, expected.Subjects) {
		n.log.Warn().Str("field", "Subjects").Interface("current", current.Subjects).Interface("expected", expected.Subjects).Msg(configMismatchMessage)
		return false
	}

	if current.Retention != expected.Retention {
		n.log.Warn().Str("field", "Retention").Interface("current", current.Retention).Interface("expected", expected.Retention).Msg(configMismatchMessage)
		return false
	}

	if current.Storage != expected.Storage {
		n.log.Warn().Str("field", "Storage").Interface("current", current.Storage).Interface("expected", expected.Storage).Msg(configMismatchMessage)
		return false
	}

	if current.Replicas != expected.Replicas {
		n.log.Warn().Str("field", "Replicas").Int("current", current.Replicas).Int("expected", expected.Replicas).Msg(configMismatchMessage)
		return false
	}

	return true
}

// compareLimitFields compares limit-related fields
func (n *natsReady) compareLimitFields(current, expected *jetstream.StreamConfig) bool {
	if current.MaxConsumers != expected.MaxConsumers {
		n.log.Warn().Str("field", "MaxConsumers").Int("current", current.MaxConsumers).Int("expected", expected.MaxConsumers).Msg(configMismatchMessage)
		return false
	}

	if current.MaxMsgsPerSubject != expected.MaxMsgsPerSubject {
		n.log.Warn().Str("field", "MaxMsgsPerSubject").Int64("current", current.MaxMsgsPerSubject).Int64("expected", expected.MaxMsgsPerSubject).Msg(configMismatchMessage)
		return false
	}

	if current.MaxMsgs != expected.MaxMsgs {
		n.log.Warn().Str("field", "MaxMsgs").Int64("current", current.MaxMsgs).Int64("expected", expected.MaxMsgs).Msg(configMismatchMessage)
		return false
	}

	if current.MaxBytes != expected.MaxBytes {
		n.log.Warn().Str("field", "MaxBytes").Int64("current", current.MaxBytes).Int64("expected", expected.MaxBytes).Msg(configMismatchMessage)
		return false
	}

	if current.MaxMsgSize != expected.MaxMsgSize {
		n.log.Warn().Str("field", "MaxMsgSize").Int32("current", current.MaxMsgSize).Int32("expected", expected.MaxMsgSize).Msg(configMismatchMessage)
		return false
	}

	return true
}

// compareTimeFields compares time-based fields
func (n *natsReady) compareTimeFields(current, expected *jetstream.StreamConfig) bool {
	if current.MaxAge != expected.MaxAge {
		currentDuration := time.Duration(current.MaxAge)
		expectedDuration := time.Duration(expected.MaxAge)
		if currentDuration != expectedDuration {
			n.log.Warn().Str("field", "MaxAge").Dur("current", currentDuration).Dur("expected", expectedDuration).Msg(configMismatchMessage)
			return false
		}
	}

	if current.Duplicates != expected.Duplicates {
		currentDuplicates := time.Duration(current.Duplicates)
		expectedDuplicates := time.Duration(expected.Duplicates)
		if currentDuplicates != expectedDuplicates {
			n.log.Warn().Str("field", "Duplicates").Dur("current", currentDuplicates).Dur("expected", expectedDuplicates).Msg(configMismatchMessage)
			return false
		}
	}

	return true
}

// comparePolicyFields compares policy and behavior fields
func (n *natsReady) comparePolicyFields(current, expected *jetstream.StreamConfig) bool {
	if current.Discard != expected.Discard {
		n.log.Warn().Str("field", "Discard").Interface("current", current.Discard).Interface("expected", expected.Discard).Msg(configMismatchMessage)
		return false
	}

	if current.Sealed != expected.Sealed {
		n.log.Warn().Str("field", "Sealed").Bool("current", current.Sealed).Bool("expected", expected.Sealed).Msg(configMismatchMessage)
		return false
	}

	if current.DenyDelete != expected.DenyDelete {
		n.log.Warn().Str("field", "DenyDelete").Bool("current", current.DenyDelete).Bool("expected", expected.DenyDelete).Msg(configMismatchMessage)
		return false
	}

	if current.DenyPurge != expected.DenyPurge {
		n.log.Warn().Str("field", "DenyPurge").Bool("current", current.DenyPurge).Bool("expected", expected.DenyPurge).Msg(configMismatchMessage)
		return false
	}

	return true
}

// compareAdvancedFields compares advanced feature fields
func (n *natsReady) compareAdvancedFields(current, expected *jetstream.StreamConfig) bool {
	if current.AllowRollup != expected.AllowRollup {
		n.log.Warn().Str("field", "AllowRollup").Bool("current", current.AllowRollup).Bool("expected", expected.AllowRollup).Msg(configMismatchMessage)
		return false
	}

	if current.AllowDirect != expected.AllowDirect {
		n.log.Warn().Str("field", "AllowDirect").Bool("current", current.AllowDirect).Bool("expected", expected.AllowDirect).Msg(configMismatchMessage)
		return false
	}

	if current.MirrorDirect != expected.MirrorDirect {
		n.log.Warn().Str("field", "MirrorDirect").Bool("current", current.MirrorDirect).Bool("expected", expected.MirrorDirect).Msg(configMismatchMessage)
		return false
	}

	if !reflect.DeepEqual(current.ConsumerLimits, expected.ConsumerLimits) {
		n.log.Warn().Str("field", "ConsumerLimits").Interface("current", current.ConsumerLimits).Interface("expected", expected.ConsumerLimits).Msg(configMismatchMessage)
		return false
	}

	return true
}
