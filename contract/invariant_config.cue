package contract

// Cross-configuration invariants.
//
// Seven config files, each parsed separately by the kernel with its own version
// check, each internally valid. Nothing held them in one namespace and asked
// whether they AGREE — which is how two independence-critical roles came to be
// bound to a harness whose own profile records it as ruled-out. No single file
// is wrong; the set is.
//
// Every invariant yields a map of subject to reason, so a failure names the
// offender. An empty map is the pass condition.

import "strings"

_roles:      configs.roles.data.roles
_treatments: {for item in configs["role-treatments"].data.role_treatments {"\(item.id)": item}}
_harnesses:  configs["harness-profiles"].data.harnesses
_phases:     configs.workflow.data.phases

// The harness each role reaches, transitively, where that chain resolves.
_roleHarness: {
	for name, role in _roles
	if (_treatments & {"\(role.role_treatment)": _}) != _|_
	for id, treatment in _treatments
	if id == role.role_treatment {
		"\(name)": treatment.harness
	}
}

// Whether the treatment a role binds is enabled. A ruled-out harness behind a
// disabled treatment cannot execute; behind an enabled one it can.
_roleEnabled: {
	for name, role in _roles
	for id, treatment in _treatments
	if id == role.role_treatment {
		"\(name)": treatment.enabled
	}
}

// C-CONFIG-001 — a role reaches a harness whose profile is ruled out.
// The defect this file was written for. It spans three files and none of them
// is individually wrong: roles.v1.json names a treatment, role-treatments.v1.json
// names a harness, harness-profiles.v1.json rules that harness out.
//
// Split by reachability rather than waived. A waiver has to be remembered; this
// arms itself. While the treatment is disabled the finding is DEFERRED and
// reported without failing; the moment anyone sets enabled: true it becomes a
// hard diagnostic, with no human in the loop to forget.
_cConfig001: {
	for name, harness in _roleHarness
	for id, profile in _harnesses
	if id == harness && profile.version_pin == "ruled-out" && _roleEnabled[name] {
		"\(name)": "role reaches harness '\(harness)', whose profile records version_pin: ruled-out, and its treatment is ENABLED"
	}
}

_deferred001: {
	for name, harness in _roleHarness
	for id, profile in _harnesses
	if id == harness && profile.version_pin == "ruled-out" && !_roleEnabled[name] {
		"\(name)": "role reaches harness '\(harness)', whose profile records version_pin: ruled-out — latent only because its treatment is disabled; resolve before arming"
	}
}

// C-CONFIG-002 — a role names a Role-Treatment that does not exist.
_cConfig002: {
	for name, role in _roles
	let hits = [for id, _ in _treatments if id == role.role_treatment {id}]
	if len(hits) != 1 {
		"\(name)": "role_treatment '\(role.role_treatment)' matches \(len(hits)) declared treatments, expected exactly 1"
	}
}

// C-CONFIG-003 — a Role-Treatment names a harness with no profile.
_cConfig003: {
	for id, treatment in _treatments
	let hits = [for h, _ in _harnesses if h == treatment.harness {h}]
	if len(hits) != 1 {
		"\(id)": "harness '\(treatment.harness)' matches \(len(hits)) declared profiles, expected exactly 1"
	}
}

// C-CONFIG-004 — a Role-Treatment disagrees with the role that binds it.
// Both files name the role; if they diverge, one of them is lying about intent.
_cConfig004: {
	for name, role in _roles
	for id, treatment in _treatments
	if id == role.role_treatment && treatment.role != name {
		"\(name)": "role binds treatment '\(id)', which declares role '\(treatment.role)'"
	}
}

// C-CONFIG-005 — a workflow phase dispatches to a role that does not exist.
_cConfig005: {
	for phaseName, phase in _phases
	if phase.role != null
	let hits = [for name, _ in _roles if name == phase.role {name}]
	if len(hits) != 1 {
		"\(phaseName)": "phase dispatches to role '\(phase.role)', which matches \(len(hits)) declared roles"
	}
}

// C-CONFIG-006 — a workflow transition targets a phase that does not exist,
// including the initial phase. A dangling transition is a loop that cannot close.
_cConfig006: {
	for phaseName, phase in _phases
	for event, target in phase.on
	let hits = [for other, _ in _phases if other == target {other}]
	if len(hits) != 1 {
		"\(phaseName).\(event)": "transition targets phase '\(target)', which does not exist"
	}
}

_cConfig006b: {
	let hits = [for name, _ in _phases if name == configs.workflow.data.initial {name}]
	if len(hits) != 1 {
		"initial": "workflow.initial names phase '\(configs.workflow.data.initial)', which does not exist"
	}
}

// C-CONFIG-007 — an independence rule names a role that does not exist.
// Independence is the externally meaningful control; a rule over a phantom role
// constrains nothing.
_cConfig007: {
	for index, rule in configs.roles.data.independence
	let subject = [for name, _ in _roles if name == rule.role {name}]
	let other = [for name, _ in _roles if name == rule.from_role {name}]
	if len(subject) != 1 || len(other) != 1 {
		"independence[\(index)]": "rule relates '\(rule.role)' and '\(rule.from_role)'; \(len(subject)) and \(len(other)) matching roles declared"
	}
}

// C-CONFIG-008 — a role reaches a harness that declares no version pin at all.
// An unpinned harness is a drift surface, not a configuration.
_cConfig008: {
	for name, harness in _roleHarness
	for id, profile in _harnesses
	if id == harness && strings.TrimSpace(profile.version_pin) == "" {
		"\(name)": "role reaches harness '\(harness)', whose profile declares an empty version_pin"
	}
}

// Findings that cannot bite in the current posture. Reported loudly, never
// silently: a deferred finding that nobody prints is a waiver with extra steps.
deferred: {
	for subject, reason in _deferred001 {"C-CONFIG-001 \(subject)": reason}
	for subject, reason in _deferredCli005 {"C-CLI-005 \(subject)": reason}
}

// C-CONFIG-009 — a Role-Treatment id must not encode which vendor or model
// serves it. Ids like "independent-adversary-grok-build-grok45-high-v1" mean a
// role knows its vendor by name, so swapping one touches every file that names
// the id. The binding belongs in exactly one place: this table's harness and
// model_route fields.
//
// Without this check the abstraction decays the first time someone writes a
// descriptive id, and nothing complains. With it, the old shape is unwritable.
_cConfig009: {
	for id, treatment in _treatments
	for harness, _ in _harnesses
	if strings.Contains(id, harness) {
		"\(id)": "Role-Treatment id encodes the harness name '\(harness)' — put the binding in the harness field, not the id"
	}
}

_cConfig009b: {
	for id, treatment in _treatments
	let selector = strings.ToLower(treatment.model_route.selector)
	if selector != "" && strings.Contains(strings.ToLower(id), selector) {
		"\(id)": "Role-Treatment id encodes the model selector '\(treatment.model_route.selector)' — put it in model_route, not the id"
	}
}

diagnostics: {
	for subject, reason in _cConfig001 {"C-CONFIG-001 \(subject)": reason}
	for subject, reason in _cConfig002 {"C-CONFIG-002 \(subject)": reason}
	for subject, reason in _cConfig003 {"C-CONFIG-003 \(subject)": reason}
	for subject, reason in _cConfig004 {"C-CONFIG-004 \(subject)": reason}
	for subject, reason in _cConfig005 {"C-CONFIG-005 \(subject)": reason}
	for subject, reason in _cConfig006 {"C-CONFIG-006 \(subject)": reason}
	for subject, reason in _cConfig006b {"C-CONFIG-006 \(subject)": reason}
	for subject, reason in _cConfig007 {"C-CONFIG-007 \(subject)": reason}
	for subject, reason in _cConfig008 {"C-CONFIG-008 \(subject)": reason}
	for subject, reason in _cConfig009 {"C-CONFIG-009 \(subject)": reason}
	for subject, reason in _cConfig009b {"C-CONFIG-009 \(subject)": reason}
	for subject, reason in _cCli001 {"C-CLI-001 \(subject)": reason}
	for subject, reason in _cCli002 {"C-CLI-002 \(subject)": reason}
	for subject, reason in _cCli003 {"C-CLI-003 \(subject)": reason}
	for subject, reason in _cCli004 {"C-CLI-004 \(subject)": reason}
	for subject, reason in _cCli005 {"C-CLI-005 \(subject)": reason}
	for subject, reason in _cSerena001 {"C-SERENA-001 \(subject)": reason}
	for subject, reason in _cSerena001b {"C-SERENA-001 \(subject)": reason}
	for subject, reason in _cSerena002 {"C-SERENA-002 \(subject)": reason}
	for subject, reason in _cSerena003 {"C-SERENA-003 \(subject)": reason}
	for subject, reason in _cSerena004 {"C-SERENA-004 \(subject)": reason}
	for subject, reason in _cSerena005 {"C-SERENA-005 \(subject)": reason}
	for subject, reason in _cSerena005b {"C-SERENA-005 \(subject)": reason}
	for subject, reason in _cSerena006 {"C-SERENA-006 \(subject)": reason}
	for subject, reason in _cSerena007 {"C-SERENA-007 \(subject)": reason}
}
