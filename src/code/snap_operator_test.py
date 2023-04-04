# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import datetime
import time
import unittest
from unittest import mock
from typing import Iterator

from . import configs
from . import deletion_logic
from . import snap_holder
from . import snap_operator

# For testing, we can access private methods.
# pyright: reportPrivateUsage=false

# UTC time.
# Alternative to using pytz.localize(...), and removes dependency on pytz.
_FAKE_NOW = datetime.datetime(2023, 2, 15, hour=12, minute=0, second=0)


def _utc_to_local(yyyymmddhhmmss: str) -> datetime.datetime:
    return (
        (
            datetime.datetime.strptime(yyyymmddhhmmss, "%Y%m%d%H%M%S")
            - datetime.timedelta(seconds=time.timezone)
        )
        .astimezone()
        .replace(tzinfo=None)
    )


def _utc_to_local_str(yyyymmddhhmmss: str) -> str:
    return _utc_to_local(yyyymmddhhmmss).strftime("%Y%m%d%H%M%S")


class SnapOperatorTest(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self._old_snaps: list[snap_holder.Snapshot] = []

    def test_scheduled_without_preexisting(self):
        snapper = snap_operator.SnapOperator(
            config=configs.Config(
                config_file="config_file",
                source="snap_source",
                dest_prefix="dest_prefix",
            ),
            now=_FAKE_NOW,
        )
        snapper.scheduled()
        self._mock_create_from.assert_called_with("snap_source")

    def test_scheduled_not_triggered(self):
        self._old_snaps = [
            snap_holder.Snapshot(
                # Added 10 minutes, to counteract DURATION_BUFFER.
                "/tmp/nodir/@home-" + _utc_to_local_str("20230213" "001000")
            )
        ]
        self._old_snaps[-1].metadata.trigger = "S"
        trigger_interval = datetime.timedelta(hours=12).total_seconds()
        snapper = snap_operator.SnapOperator(
            config=configs.Config(
                config_file="config_file",
                source="snap_source",
                dest_prefix="dest_prefix",
                trigger_interval=trigger_interval,
            ),
            now=_utc_to_local("20230213" "110000"),
        )
        snapper.scheduled()
        self._mock_delete.assert_not_called()
        self._mock_create_from.assert_not_called()

    def test_scheduled_triggered(self):
        self._old_snaps = [
            snap_holder.Snapshot(
                # Added 10 minutes, to counteract DURATION_BUFFER.
                "/tmp/nodir/@home-" + _utc_to_local_str("20230213" "001000")
            )
        ]
        self._old_snaps[-1].metadata.trigger = "S"
        trigger_interval = datetime.timedelta(hours=12).total_seconds()
        snapper = snap_operator.SnapOperator(
            config=configs.Config(
                config_file="config_file",
                source="snap_source",
                dest_prefix="dest_prefix",
                trigger_interval=trigger_interval,
            ),
            now=_utc_to_local("20230213" "130000"),
        )
        snapper.scheduled()
        self._mock_delete.assert_called_once_with()
        self._mock_create_from.assert_called_with("snap_source")

    def setUp(self) -> None:
        super().setUp()
        self._exit_stack = contextlib.ExitStack()
        self._mock_delete = mock.MagicMock()
        self._exit_stack.enter_context(
            mock.patch.object(snap_holder.Snapshot, "delete", self._mock_delete)
        )
        self._mock_create_from = mock.MagicMock()
        self._exit_stack.enter_context(
            mock.patch.object(
                snap_holder.Snapshot, "create_from", self._mock_create_from
            )
        )

        def fake_get_deletes(
            self, now: datetime.datetime, records: list[tuple[datetime.datetime, str]]
        ) -> Iterator[tuple[datetime.datetime, str]]:
            for when, pathname in records:
                if pathname != "":
                    yield when, pathname

        self._exit_stack.enter_context(
            mock.patch.object(
                deletion_logic.DeleteManager, "get_deletes", fake_get_deletes
            )
        )
        self._exit_stack.enter_context(
            mock.patch.object(
                snap_operator, "_get_old_backups", lambda configs: self._old_snaps
            )
        )

    def tearDown(self) -> None:
        self._exit_stack.close()
        super().tearDown()


if __name__ == "__main__":
    unittest.main()