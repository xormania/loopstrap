from __future__ import annotations

from dataclasses import dataclass

from .errors import ContextBoundaryError


@dataclass(frozen=True)
class ContextManifest:
    role_kind: str
    artifact_refs: dict[str, str]

    TESTS_FORBIDDEN = {
        "implementation",
        "candidate_diff",
        "patch",
        "transcript",
        "source",
        "code",
        "full_log",
    }

    @classmethod
    def for_role(cls, *, role_kind: str, artifact_refs: dict[str, str]) -> "ContextManifest":
        refs = {str(key): str(value) for key, value in artifact_refs.items()}
        if role_kind == "tests":
            forbidden = sorted(set(refs) & cls.TESTS_FORBIDDEN)
            if forbidden:
                raise ContextBoundaryError(
                    f"test-writing context contains implementation material: {forbidden}"
                )
        return cls(role_kind=role_kind, artifact_refs=refs)

