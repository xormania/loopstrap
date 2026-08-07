package contract

// One invariant. It is here because it caught a real defect: spec/cue/evidence.cue
// required `treatment_id` while loopstrap_core/evidence.py required
// `role_treatment_id`, and EvidenceCompiler ran both over the same document. No
// evidence record could satisfy both, so acceptance-check could not accept any
// input, for a week, behind a green battery.
//
// Every other check that lived in this file was plausible and had never fired on
// anything real. They were deleted. An invariant earns permanence by catching
// something; until then it is a guess with a diagnostic code.

import (
	"list"
	"strings"
)

// C-SCHEMA-001 — a declared pair disagrees on required field names.
_cSchema001: {
	for pair in pairs
	let py = [for fact in python if fact.label == pair.pythonLabel {fact}]
	let cu = [for fact in cue if fact.definition == pair.definition {fact}]
	if len(py) == 1 && len(cu) == 1
	let cuFields = list.Concat([cu[0].fields, pair.optional])
	let onlyPy = [for f in py[0].fields if !list.Contains(cuFields, f) {f}]
	let onlyCue = [for f in cu[0].fields if !list.Contains(py[0].fields, f) {f}]
	if len(onlyPy) > 0 || len(onlyCue) > 0 {
		"\(pair.pythonLabel) vs \(pair.definition)": "field sets disagree — only in Python: [\(strings.Join(onlyPy, ", "))]; only in CUE: [\(strings.Join(onlyCue, ", "))]"
	}
}

diagnostics: {
	for subject, reason in _cSchema001 {"C-SCHEMA-001 \(subject)": reason}
	for subject, reason in _cLane001 {"C-LANE-001 \(subject)": reason}
	for subject, reason in _cLane002 {"C-LANE-002 \(subject)": reason}
}
