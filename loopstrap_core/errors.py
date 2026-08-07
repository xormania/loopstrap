"""Typed refusal classes. Callers must not convert these into success."""


class LoopstrapError(Exception):
    pass


class SchemaError(LoopstrapError):
    pass


class AuthorityError(LoopstrapError):
    pass


class StaleResultError(LoopstrapError):
    pass


class TransitionError(LoopstrapError):
    pass


class DecompositionError(LoopstrapError):
    pass


class ClosureError(LoopstrapError):
    pass


class ContextBoundaryError(LoopstrapError):
    pass


class IntegrityError(LoopstrapError):
    pass


class IdempotencyError(LoopstrapError):
    pass


class SensitiveDataError(LoopstrapError):
    pass


class WorkspaceBoundaryError(LoopstrapError):
    pass


class PromotionError(LoopstrapError):
    pass


class RoleTreatmentUnavailableError(LoopstrapError):
    def __init__(self, role_treatment_id: str) -> None:
        self.role_treatment_id = role_treatment_id
        super().__init__(
            f"required Role-Treatment unavailable: {role_treatment_id}"
        )


class IndependenceError(LoopstrapError):
    pass


class HarnessExecutionError(LoopstrapError):
    def __init__(
        self,
        message: str,
        *,
        stdout: bytes = b"",
        stderr: bytes = b"",
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.execution_ref: str | None = None
        self.raw_redaction_count = 0
        self.process_trace: dict[str, object] | None = None
        super().__init__(message)


class HarnessProtocolError(HarnessExecutionError):
    pass


class HarnessTimeoutError(HarnessExecutionError):
    pass


class HarnessOutputLimitError(HarnessExecutionError):
    pass


class HarnessInterruptedError(HarnessExecutionError):
    pass


class LiveHarnessDisabledError(LoopstrapError):
    pass


class EvidenceError(LoopstrapError):
    pass


class SpecificationError(LoopstrapError):
    pass


class CertificationError(LoopstrapError):
    pass
