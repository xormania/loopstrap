package contract

// Symbolic-tooling bindings, checked against what the roles already declare.
//
// The point of this file is capability, not ceremony. Every invariant here
// catches a CONTRADICTION between two things the configuration already says —
// none of them adds a step anyone has to perform. A process that suffocates
// development is one that makes you do more; this one only complains when the
// configuration disagrees with itself.

import (
	"list"
	"strings"
)

_serena:      configs.serena.data
_serenaRoles: _serena.roles

// Permission modes that let a role change the tree. `disposable-` still writes;
// the disposability is about what happens to the workspace afterwards, not about
// whether edits occur, so it belongs on the writing side.
_writingModes: ["workspace-write", "disposable-workspace-write"]
_nonWritingModes: ["plan", "read-only"]

_treatmentMode: {
	for id, treatment in _treatments {
		"\(id)": treatment.configuration.permissions.mode
	}
}

_treatmentWrites: {
	for id, mode in _treatmentMode {
		"\(id)": list.Contains(_writingModes, mode)
	}
}

// C-SERENA-001 — two surfaces, two locks.
// Project-level read_only strips Serena's editing tools structurally, but it
// cannot touch the host harness's native edit tools. A role that may not write
// must be locked on BOTH surfaces; either one alone leaves a hole.
_cSerena001: {
	for id, binding in _serenaRoles
	if (_treatmentWrites & {"\(id)": _}) != _|_
	for treatmentId, writes in _treatmentWrites
	if treatmentId == id && binding.read_only && writes {
		"\(id)": "Serena binding is read_only but the Role-Treatment permits workspace_write — one surface locked, the other open"
	}
}

_cSerena001b: {
	for id, binding in _serenaRoles
	for treatmentId, writes in _treatmentWrites
	if treatmentId == id && !binding.read_only && !writes {
		"\(id)": "Role-Treatment forbids workspace_write but the Serena binding is not read_only — the harness lock is bypassable through symbolic edits"
	}
}

// C-SERENA-002 — every bound role must exist.
_cSerena002: {
	for id, _ in _serenaRoles
	let hits = [for treatmentId, _ in _treatments if treatmentId == id {treatmentId}]
	if len(hits) != 1 {
		"\(id)": "Serena binding names a Role-Treatment that does not exist"
	}
}

// C-SERENA-003 — every Role-Treatment should have a decision recorded.
// Silence is not a decision: an unbound role is one nobody thought about.
_cSerena003: {
	for id, _ in _treatments
	let hits = [for boundId, _ in _serenaRoles if boundId == id {boundId}]
	if len(hits) != 1 {
		"\(id)": "Role-Treatment has no Serena binding — decide explicitly, including deciding not to enable it"
	}
}

// C-SERENA-004 — the tool timeout must be bounded well below the default.
// Serena's 240s default is a sane library default and a bad loop default: a
// wedged language server is allowed to cost four minutes of a run.
_cSerena004: {
	if _serena.tool_timeout_seconds > 120 || _serena.tool_timeout_seconds < 10 {
		"tool_timeout_seconds": "must be between 10 and 120; \(_serena.tool_timeout_seconds) is outside the range a loop can absorb (Serena's own minimum is 10, its default 240)"
	}
}

// C-SERENA-005 — reference counts must not be treated as probed evidence
// unless the index is warmed first.
//
// This is the one that matters. Language servers without a readiness wait return
// partial results SILENTLY during indexing, so an early "no references found" is
// indistinguishable from "not indexed yet". Recording it as probed evidence
// would put a green that means nothing into the evidence chain.
_cSerena005: {
	if !_serena.reference_evidence.requires_warm_index {
		"reference_evidence": "requires_warm_index is false — a cold-index reference count is indistinguishable from an unindexed one, and must never be admitted as probed evidence"
	}
}

_cSerena005b: {
	if _serena.reference_evidence.cold_index_status == "probed" {
		"reference_evidence": "cold_index_status is 'probed'; a count taken before the index is warm was not observed, it was guessed at"
	}
}

// C-SERENA-006 — only language servers this system is willing to depend on.
_cSerena006: {
	let banned = ["bsl", "fsharp", "f#", "kotlin"]
	for language in _serena.reliable_languages
	if list.Contains(banned, language) {
		"\(language)": "listed as reliable, but Serena's own suite disables it as flaky or unreliable"
	}
}

// C-SERENA-007 — an unrecognised permission mode.
// Modes decide whether a role may write, so a typo silently lands the role on
// the non-writing side and every downstream check agrees with the typo.
_cSerena007: {

	let known = list.Concat([_writingModes, _nonWritingModes])
	for id, mode in _treatmentMode
	if !list.Contains(known, mode) {
		"\(id)": "permission mode '\(mode)' is not one of [\(strings.Join(known, ", "))] — a mode nobody recognises is treated as non-writing, which fails open"
	}
}
