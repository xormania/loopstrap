package contract

// Lane separation, mechanically.
//
// skills/dev/lane-classification/SKILL.md teaches the judgement — the part that
// needs a person. These two catch the part that does not: a development package
// name inside the shipped contract surface, and a production file naming
// development machinery.
//
// Both failures are invisible until something that should have been impossible
// happens, which is why they are worth a check rather than a convention.

import "strings"

// C-LANE-001 — a production CUE file declaring the development package.
// The development package is `contract`, singular; production uses `contracts`,
// `evidence`, `project`. Sharing a package name is enough for a development
// expectation to unify into the shipped surface, even from a separate file.
_cLane001: {
	for fact in lanes
	if fact.package == "contract" {
		"\(fact.file)": "declares the development package name — a development expectation could unify into the shipped contract surface"
	}
}

// C-LANE-002 — a production file naming development machinery.
_cLane002: {
	for fact in lanes
	if len(fact.references) > 0 {
		"\(fact.file)": "references development machinery [\(strings.Join(fact.references, ", "))] — production must survive being separated from this repository"
	}
}

