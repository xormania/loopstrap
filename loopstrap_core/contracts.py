from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from .atomic import canonical_json
from .errors import DecompositionError, SchemaError
from .specification import CUECompiler, SpecificationSnapshot


RESPONSIBILITY_MODES = {"exclusive", "shared", "supporting", "composite"}
SCOPE_KINDS = {"cell", "composite", "root"}


def _exact(data: dict[str, Any], fields: set[str], label: str) -> None:
    if not isinstance(data, dict) or set(data) != fields:
        missing = fields - set(data) if isinstance(data, dict) else fields
        unknown = set(data) - fields if isinstance(data, dict) else set()
        raise SchemaError(
            f"{label} fields invalid: missing={sorted(missing)} unknown={sorted(unknown)}"
        )


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaError(f"{label} must be a nonempty string")
    return value


def _strings(value: Any, label: str, *, nonempty: bool = True) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise SchemaError(f"{label} must be a {'nonempty ' if nonempty else ''}string list")
    rows = tuple(value)
    if len(set(rows)) != len(rows):
        raise SchemaError(f"{label} must not contain duplicates")
    return rows


@dataclass(frozen=True)
class PortContract:
    port_id: str
    schema_ref: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PortContract":
        _exact(data, {"id", "schema_ref"}, "port contract")
        return cls(
            port_id=_text(data["id"], "port id"),
            schema_ref=_text(data["schema_ref"], "port schema reference"),
        )


@dataclass(frozen=True)
class VerificationObligationContract:
    obligation_id: str
    scope_kind: str
    eligible_producer_classes: tuple[str, ...]
    minimum_evidence: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationObligationContract":
        _exact(
            data,
            {
                "id",
                "scope_kind",
                "eligible_producer_classes",
                "minimum_evidence",
            },
            "verification obligation",
        )
        scope_kind = _text(data["scope_kind"], "verification scope kind")
        if scope_kind not in SCOPE_KINDS:
            raise SchemaError(f"unsupported verification scope kind: {scope_kind}")
        minimum = data["minimum_evidence"]
        if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
            raise SchemaError("minimum evidence must be a positive integer")
        return cls(
            obligation_id=_text(data["id"], "verification obligation id"),
            scope_kind=scope_kind,
            eligible_producer_classes=_strings(
                data["eligible_producer_classes"],
                "eligible producer classes",
            ),
            minimum_evidence=minimum,
        )


@dataclass(frozen=True)
class GuaranteeContract:
    guarantee_id: str
    responsibility: str
    contract_refs: tuple[str, ...]
    verification_obligation_ids: tuple[str, ...]
    supported_by: tuple[str, ...] = ()

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        composite: bool,
    ) -> "GuaranteeContract":
        fields = {
            "id",
            "responsibility",
            "contract_refs",
            "verification_obligation_ids",
        }
        if composite:
            fields.add("supported_by")
        _exact(data, fields, "guarantee contract")
        responsibility = _text(data["responsibility"], "responsibility mode")
        if responsibility not in RESPONSIBILITY_MODES:
            raise SchemaError(f"unsupported responsibility mode: {responsibility}")
        if composite and responsibility != "composite":
            raise SchemaError("composite guarantees require composite responsibility")
        if not composite and responsibility == "composite":
            raise SchemaError("member Cell guarantee cannot claim composite responsibility")
        return cls(
            guarantee_id=_text(data["id"], "guarantee id"),
            responsibility=responsibility,
            contract_refs=_strings(data["contract_refs"], "guarantee contract references"),
            verification_obligation_ids=_strings(
                data["verification_obligation_ids"],
                "guarantee verification obligation ids",
            ),
            supported_by=(
                _strings(data["supported_by"], "supporting guarantees", nonempty=False)
                if composite
                else ()
            ),
        )


@dataclass(frozen=True)
class CellContract:
    cell_id: str
    contract_refs: tuple[str, ...]
    inputs: tuple[PortContract, ...]
    outputs: tuple[PortContract, ...]
    guarantees: tuple[GuaranteeContract, ...]
    failures: tuple[str, ...]
    owned_effects: tuple[str, ...]
    dependencies: tuple[str, ...]
    invariants: tuple[str, ...]
    verification_obligations: tuple[VerificationObligationContract, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CellContract":
        _exact(
            data,
            {
                "id",
                "contract_refs",
                "inputs",
                "outputs",
                "guarantees",
                "failures",
                "owned_effects",
                "dependencies",
                "invariants",
                "verification_obligations",
            },
            "Cell contract",
        )
        if not isinstance(data["inputs"], list) or not data["inputs"]:
            raise SchemaError("Cell inputs must be a nonempty list")
        if not isinstance(data["outputs"], list) or not data["outputs"]:
            raise SchemaError("Cell outputs must be a nonempty list")
        if not isinstance(data["guarantees"], list) or not data["guarantees"]:
            raise SchemaError("Cell guarantees must be a nonempty list")
        if (
            not isinstance(data["verification_obligations"], list)
            or not data["verification_obligations"]
        ):
            raise SchemaError("Cell verification obligations must be a nonempty list")
        cell = cls(
            cell_id=_text(data["id"], "Cell id"),
            contract_refs=_strings(data["contract_refs"], "Cell contract references"),
            inputs=tuple(PortContract.from_dict(item) for item in data["inputs"]),
            outputs=tuple(PortContract.from_dict(item) for item in data["outputs"]),
            guarantees=tuple(
                GuaranteeContract.from_dict(item, composite=False)
                for item in data["guarantees"]
            ),
            failures=_strings(data["failures"], "Cell failures"),
            owned_effects=_strings(data["owned_effects"], "Cell owned effects"),
            dependencies=_strings(
                data["dependencies"], "Cell dependencies", nonempty=False
            ),
            invariants=_strings(data["invariants"], "Cell invariants"),
            verification_obligations=tuple(
                VerificationObligationContract.from_dict(item)
                for item in data["verification_obligations"]
            ),
        )
        cell.validate()
        return cell

    def validate(self) -> None:
        input_ids = [port.port_id for port in self.inputs]
        output_ids = [port.port_id for port in self.outputs]
        if len(set(input_ids)) != len(input_ids) or len(set(output_ids)) != len(output_ids):
            raise SchemaError(f"Cell ports must be unique: {self.cell_id}")
        guarantee_ids = [item.guarantee_id for item in self.guarantees]
        if len(set(guarantee_ids)) != len(guarantee_ids):
            raise SchemaError(f"Cell guarantees must be unique: {self.cell_id}")
        obligation_ids = {
            item.obligation_id for item in self.verification_obligations
        }
        if len(obligation_ids) != len(self.verification_obligations):
            raise SchemaError(f"Cell verification obligations must be unique: {self.cell_id}")
        for guarantee in self.guarantees:
            if not set(guarantee.contract_refs).issubset(self.contract_refs):
                raise SchemaError(
                    f"Cell guarantee cites an undeclared project contract: {guarantee.guarantee_id}"
                )
            if not set(guarantee.verification_obligation_ids).issubset(obligation_ids):
                raise SchemaError(
                    f"Cell guarantee cites an unknown verification obligation: {guarantee.guarantee_id}"
                )
        if any(item.scope_kind != "cell" for item in self.verification_obligations):
            raise SchemaError(f"Cell verification obligation has the wrong scope: {self.cell_id}")

    def input(self, port_id: str) -> PortContract:
        matches = [item for item in self.inputs if item.port_id == port_id]
        if len(matches) != 1:
            raise DecompositionError(
                f"unknown or duplicate Cell input port: {self.cell_id}.{port_id}"
            )
        return matches[0]

    def output(self, port_id: str) -> PortContract:
        matches = [item for item in self.outputs if item.port_id == port_id]
        if len(matches) != 1:
            raise DecompositionError(
                f"unknown or duplicate Cell output port: {self.cell_id}.{port_id}"
            )
        return matches[0]


@dataclass(frozen=True)
class PortReference:
    cell_id: str
    port_id: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PortReference":
        _exact(data, {"cell_id", "port_id"}, "port reference")
        return cls(
            cell_id=_text(data["cell_id"], "port reference Cell id"),
            port_id=_text(data["port_id"], "port reference port id"),
        )


@dataclass(frozen=True)
class ConnectionContract:
    source: PortReference
    target: PortReference

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConnectionContract":
        _exact(data, {"source", "target"}, "connection contract")
        return cls(
            source=PortReference.from_dict(data["source"]),
            target=PortReference.from_dict(data["target"]),
        )


@dataclass(frozen=True)
class CompositeCellContract:
    composite_id: str
    controlling_cell_id: str | None
    members: tuple[str, ...]
    connections: tuple[ConnectionContract, ...]
    external_inputs: tuple[PortReference, ...]
    external_outputs: tuple[PortReference, ...]
    guarantees: tuple[GuaranteeContract, ...]
    failures: tuple[str, ...]
    invariants: tuple[str, ...]
    verification_obligations: tuple[VerificationObligationContract, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompositeCellContract":
        fields = {
            "id",
            "members",
            "connections",
            "external_inputs",
            "external_outputs",
            "guarantees",
            "failures",
            "invariants",
            "verification_obligations",
        }
        if set(data) == fields | {"cell_id"}:
            controlling_cell_id = _text(data["cell_id"], "controlling Cell id")
        else:
            _exact(data, fields, "composite Cell contract")
            controlling_cell_id = None
        for field in (
            "connections",
            "external_inputs",
            "external_outputs",
            "guarantees",
            "verification_obligations",
        ):
            if not isinstance(data[field], list) or not data[field]:
                raise SchemaError(f"composite Cell {field} must be a nonempty list")
        composite = cls(
            composite_id=_text(data["id"], "composite Cell id"),
            controlling_cell_id=controlling_cell_id,
            members=_strings(data["members"], "composite Cell members"),
            connections=tuple(
                ConnectionContract.from_dict(item) for item in data["connections"]
            ),
            external_inputs=tuple(
                PortReference.from_dict(item) for item in data["external_inputs"]
            ),
            external_outputs=tuple(
                PortReference.from_dict(item) for item in data["external_outputs"]
            ),
            guarantees=tuple(
                GuaranteeContract.from_dict(item, composite=True)
                for item in data["guarantees"]
            ),
            failures=_strings(data["failures"], "composite Cell failures"),
            invariants=_strings(data["invariants"], "composite Cell invariants"),
            verification_obligations=tuple(
                VerificationObligationContract.from_dict(item)
                for item in data["verification_obligations"]
            ),
        )
        obligation_ids = {
            item.obligation_id for item in composite.verification_obligations
        }
        if len(obligation_ids) != len(composite.verification_obligations):
            raise SchemaError(
                f"composite verification obligations must be unique: {composite.composite_id}"
            )
        for guarantee in composite.guarantees:
            if not set(guarantee.verification_obligation_ids).issubset(obligation_ids):
                raise SchemaError(
                    f"composite guarantee cites an unknown verification obligation: {guarantee.guarantee_id}"
                )
        if any(
            item.scope_kind not in {"composite", "root"}
            for item in composite.verification_obligations
        ):
            raise SchemaError(
                f"composite verification obligation has the wrong scope: {composite.composite_id}"
            )
        return composite


@dataclass(frozen=True)
class ContractGraph:
    version: int
    specification_digest: str
    root_composite_id: str
    cells: tuple[CellContract, ...]
    composites: tuple[CompositeCellContract, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContractGraph":
        _exact(
            data,
            {
                "version",
                "specification_digest",
                "root_composite_id",
                "cells",
                "composites",
            },
            "contract graph",
        )
        version = data["version"]
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise SchemaError("contract graph version must be a positive integer")
        if not isinstance(data["cells"], list) or not data["cells"]:
            raise SchemaError("contract graph Cells must be a nonempty list")
        if not isinstance(data["composites"], list) or not data["composites"]:
            raise SchemaError("contract graph composites must be a nonempty list")
        graph = cls(
            version=version,
            specification_digest=_text(
                data["specification_digest"], "contract graph specification digest"
            ),
            root_composite_id=_text(
                data["root_composite_id"], "root composite Cell id"
            ),
            cells=tuple(CellContract.from_dict(item) for item in data["cells"]),
            composites=tuple(
                CompositeCellContract.from_dict(item)
                for item in data["composites"]
            ),
        )
        graph.validate()
        return graph

    def validate(self) -> None:
        cell_by_id = {cell.cell_id: cell for cell in self.cells}
        if len(cell_by_id) != len(self.cells):
            raise DecompositionError("contract graph Cell ids must be unique")
        composite_by_id = {
            composite.composite_id: composite for composite in self.composites
        }
        if len(composite_by_id) != len(self.composites):
            raise DecompositionError("composite Cell ids must be unique")
        if self.root_composite_id not in composite_by_id:
            raise DecompositionError("root composite Cell contract does not exist")
        controlled = [
            composite.controlling_cell_id
            for composite in self.composites
            if composite.controlling_cell_id is not None
        ]
        if len(set(controlled)) != len(controlled):
            raise DecompositionError("a Cell is controlled by more than one composite contract")
        if not set(controlled).issubset(cell_by_id):
            raise DecompositionError("a composite contract controls an unknown Cell")

        for cell in self.cells:
            unknown = set(cell.dependencies) - set(cell_by_id)
            if unknown:
                raise DecompositionError(
                    "Cell depends on undeclared Cells: "
                    f"{cell.cell_id} -> {sorted(unknown)}"
                )

        self._verify_containment_terminates(cell_by_id)

        exclusive: dict[str, str] = {}
        member_guarantees: dict[str, GuaranteeContract] = {}
        for cell in self.cells:
            for guarantee in cell.guarantees:
                member_guarantees[guarantee.guarantee_id] = guarantee
                if guarantee.responsibility != "exclusive":
                    continue
                for contract_ref in guarantee.contract_refs:
                    previous = exclusive.get(contract_ref)
                    if previous is not None:
                        raise DecompositionError(
                            "exclusive project contract responsibility overlaps: "
                            f"{contract_ref} ({previous}, {cell.cell_id})"
                        )
                    exclusive[contract_ref] = cell.cell_id

        for composite in self.composites:
            if not set(composite.members).issubset(cell_by_id):
                raise DecompositionError(
                    f"composite has unknown members: {composite.composite_id}"
                )
            for connection in composite.connections:
                if (
                    connection.source.cell_id not in composite.members
                    or connection.target.cell_id not in composite.members
                ):
                    raise DecompositionError(
                        f"connection escapes composite membership: {composite.composite_id}"
                    )
                source = cell_by_id[connection.source.cell_id].output(
                    connection.source.port_id
                )
                target = cell_by_id[connection.target.cell_id].input(
                    connection.target.port_id
                )
                if source.schema_ref != target.schema_ref:
                    raise DecompositionError(
                        "composite connection schemas are incompatible: "
                        f"{connection.source.cell_id}.{connection.source.port_id} "
                        f"({source.schema_ref}) -> "
                        f"{connection.target.cell_id}.{connection.target.port_id} "
                        f"({target.schema_ref})"
                    )
            for reference in composite.external_inputs:
                if reference.cell_id not in composite.members:
                    raise DecompositionError("external input cites a nonmember Cell")
                cell_by_id[reference.cell_id].input(reference.port_id)
            for reference in composite.external_outputs:
                if reference.cell_id not in composite.members:
                    raise DecompositionError("external output cites a nonmember Cell")
                cell_by_id[reference.cell_id].output(reference.port_id)
            for guarantee in composite.guarantees:
                unknown = set(guarantee.supported_by) - set(member_guarantees)
                if unknown:
                    raise DecompositionError(
                        "composite guarantee has unknown support: "
                        f"{guarantee.guarantee_id} -> {sorted(unknown)}"
                    )
                supporting_members = {
                    cell.cell_id
                    for cell in self.cells
                    if any(
                        item.guarantee_id in guarantee.supported_by
                        for item in cell.guarantees
                    )
                }
                if not supporting_members.issubset(composite.members):
                    raise DecompositionError(
                        f"composite guarantee support comes from a nonmember: {guarantee.guarantee_id}"
                    )
                if not guarantee.supported_by and not guarantee.verification_obligation_ids:
                    raise DecompositionError(
                        f"composite guarantee lacks support or direct verification: {guarantee.guarantee_id}"
                    )

    def _verify_containment_terminates(
        self, cell_by_id: dict[str, CellContract]
    ) -> None:
        """Refuse a containment recursion that never bottoms out.

        A composite naming `controlling_cell_id` declares itself the interior of
        that Cell, so containment is an edge from a Cell to the members of its
        interior. Composition is only recursive if that relation terminates: a
        Cell reachable from its own interior is not a decomposition, it is a
        regress, and every consumer that walks it inherits the problem.

        Unknown members are skipped rather than followed — the membership check
        below owns that diagnostic, and reporting it as a containment cycle
        would name the wrong defect.
        """
        interior = {
            composite.controlling_cell_id: composite
            for composite in self.composites
            if composite.controlling_cell_id is not None
        }
        settled: set[str] = set()
        on_path: list[str] = []

        def descend(cell_id: str) -> None:
            if cell_id in settled:
                return
            if cell_id in on_path:
                cycle = on_path[on_path.index(cell_id):] + [cell_id]
                raise DecompositionError(
                    "composite containment forms a cycle: " + " -> ".join(cycle)
                )
            on_path.append(cell_id)
            composite = interior.get(cell_id)
            if composite is not None:
                for member in composite.members:
                    if member in cell_by_id:
                        descend(member)
            on_path.pop()
            settled.add(cell_id)

        for cell in self.cells:
            descend(cell.cell_id)

    def cell(self, cell_id: str) -> CellContract:
        matches = [cell for cell in self.cells if cell.cell_id == cell_id]
        if len(matches) != 1:
            raise SchemaError(f"unknown contract graph Cell: {cell_id}")
        return matches[0]

    def composite(self, composite_id: str) -> CompositeCellContract:
        matches = [
            composite
            for composite in self.composites
            if composite.composite_id == composite_id
        ]
        if len(matches) != 1:
            raise SchemaError(f"unknown composite Cell contract: {composite_id}")
        return matches[0]

    def composite_for_cell(self, cell_id: str) -> CompositeCellContract | None:
        matches = [
            composite
            for composite in self.composites
            if composite.controlling_cell_id == cell_id
        ]
        if len(matches) > 1:
            raise SchemaError(f"Cell has multiple composite contracts: {cell_id}")
        return matches[0] if matches else None

    def to_dict(self) -> dict[str, Any]:
        result = json.loads(canonical_json(asdict(self)))
        for cell in result["cells"]:
            cell["id"] = cell.pop("cell_id")
            for port in cell["inputs"] + cell["outputs"]:
                port["id"] = port.pop("port_id")
            for guarantee in cell["guarantees"]:
                guarantee["id"] = guarantee.pop("guarantee_id")
                guarantee.pop("supported_by")
            for obligation in cell["verification_obligations"]:
                obligation["id"] = obligation.pop("obligation_id")
        for composite in result["composites"]:
            composite["id"] = composite.pop("composite_id")
            controlling = composite.pop("controlling_cell_id")
            if controlling is not None:
                composite["cell_id"] = controlling
            for guarantee in composite["guarantees"]:
                guarantee["id"] = guarantee.pop("guarantee_id")
            for obligation in composite["verification_obligations"]:
                obligation["id"] = obligation.pop("obligation_id")
        return result

    def to_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    @property
    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.to_bytes()).hexdigest()

    def validate_against_specification(
        self, specification: SpecificationSnapshot
    ) -> None:
        if self.specification_digest != specification.digest:
            raise DecompositionError(
                "contract graph and project specification digests differ"
            )
        known = {
            contract["id"]
            for contract in specification.document["contracts"]["items"]
        }
        referenced = {
            reference
            for cell in self.cells
            for reference in cell.contract_refs
        }
        unknown = referenced - known
        if unknown:
            raise DecompositionError(
                f"Cell contracts cite unknown project contracts: {sorted(unknown)}"
            )


class ContractCompiler:
    def __init__(self, cue: CUECompiler) -> None:
        self.cue = cue

    def compile(self, data: dict[str, Any]) -> ContractGraph:
        self.cue.validate_data(
            data,
            schema_file="contracts.cue",
            definition="#ContractGraph",
        )
        return ContractGraph.from_dict(data)
