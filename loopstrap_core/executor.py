from __future__ import annotations

from .workspace import WorkspaceManager


class Executor:
    def __init__(self, executor_id: str) -> None:
        self.executor_id = executor_id

    def promote(
        self,
        manager: WorkspaceManager,
        snapshot: str,
        *,
        expected_current: str,
    ) -> None:
        manager.promote(
            snapshot,
            expected_current=expected_current,
            permit=manager._executor_permit(),
        )
