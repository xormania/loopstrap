package contract

// Invariants join extracted facts against declared intent. Each produces a map
// of subject to human-readable reason rather than a boolean, so a failure names
// the offender and says what is wrong — the diagnostic IS the message.
//
// An empty `diagnostics` map is the pass condition.

import (
	"list"
	"strings"
)

_pythonByLabel: {
	for fact in python {
		"\(fact.label)": fact
	}
}

_cueByDefinition: {
	for fact in cue {
		"\(fact.definition)": fact
	}
}

// C-SCHEMA-001 — a declared pair must agree exactly on required field names.
// This is the class of defect that made acceptance-check unsatisfiable.
_cSchema001: {
	for pair in pairs
	if (_pythonByLabel & {"\(pair.pythonLabel)": _}) != _|_
	if (_cueByDefinition & {"\(pair.definition)": _}) != _|_
	let py = [for fact in python if fact.label == pair.pythonLabel {fact}]
	let cu = [for fact in cue if fact.definition == pair.definition {fact}]
	if len(py) == 1 && len(cu) == 1
	let pyFields = py[0].fields
	let cuFields = list.Concat([cu[0].fields, pair.optional])
	let onlyPy = [for f in pyFields if !list.Contains(cuFields, f) {f}]
	let onlyCue = [for f in cu[0].fields if !list.Contains(pyFields, f) {f}]
	if len(onlyPy) > 0 || len(onlyCue) > 0 {
		"\(pair.pythonLabel) vs \(pair.definition)": "field sets disagree — only in Python: [\(strings.Join(onlyPy, ", "))]; only in CUE: [\(strings.Join(onlyCue, ", "))]"
	}
}

// C-SCHEMA-002 — every declared pair must name a Python label and a CUE
// definition that actually exist. Catches a rename on either side.
_cSchema002: {
	for pair in pairs
	let py = [for fact in python if fact.label == pair.pythonLabel {fact}]
	if len(py) != 1 {
		"\(pair.pythonLabel)": "declared Python label matches \(len(py)) extracted facts, expected exactly 1"
	}
}

_cSchema002b: {
	for pair in pairs
	let cu = [for fact in cue if fact.definition == pair.definition {fact}]
	if len(cu) != 1 {
		"\(pair.definition)": "declared CUE definition matches \(len(cu)) extracted definitions, expected exactly 1"
	}
}

// C-SCHEMA-003 — every extracted Python field set must be either paired or
// explicitly declared unpaired. A new document type cannot appear on one side
// only and go unnoticed.
_cSchema003: {
	let paired = [for pair in pairs {pair.pythonLabel}]
	let excused = [for row in unpaired {row.label}]
	for fact in python
	if !list.Contains(paired, fact.label) && !list.Contains(excused, fact.label) {
		"\(fact.label)": "extracted from \(fact.module) but neither paired with a CUE definition nor declared unpaired"
	}
}

// C-SCHEMA-004 — a newly unresolvable _exact() call site is a diagnostic, so the
// extractor's blind spots stay declared rather than growing quietly.
_cSchema004: {
	let waived = [for row in waivedUnresolved {row.label}]
	for site in pythonUnresolved
	if site.label == null || !list.Contains(waived, "\(site.label)") {
		"\(site.module):\(site.line)": "unresolvable exact-field set is not waived — \(site.reason)"
	}
}

diagnostics: {
	for subject, reason in _cSchema001 {"C-SCHEMA-001 \(subject)": reason}
	for subject, reason in _cSchema002 {"C-SCHEMA-002 \(subject)": reason}
	for subject, reason in _cSchema002b {"C-SCHEMA-002 \(subject)": reason}
	for subject, reason in _cSchema003 {"C-SCHEMA-003 \(subject)": reason}
	for subject, reason in _cSchema004 {"C-SCHEMA-004 \(subject)": reason}
}
