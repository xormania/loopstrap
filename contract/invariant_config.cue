package contract

// Two invariants.
//
// C-CONFIG-001 caught a real defect: two independence-critical roles bound to a
// harness whose own profile records it ruled-out, across three files where no
// single file was wrong.
//
// C-CONFIG-009 locks in a fix rather than catching one — Role-Treatment ids no
// longer encode vendor or model, and without this the abstraction decays the
// first time someone writes a descriptive id.
//
// Everything else that lived here — dangling references, workflow reachability,
// independence membership, empty pins, and the whole harness-CLI and symbolic-
// tooling families — was plausible and had never fired on anything real. Deleted.
// They come back the day a defect they would have caught actually occurs.

import "strings"

_roles:      configs.roles.data.roles
_treatments: {for item in configs["role-treatments"].data.role_treatments {"\(item.id)": item}}
_harnesses:  configs["harness-profiles"].data.harnesses

_roleHarness: {
	for name, role in _roles
	for id, treatment in _treatments
	if id == role.role_treatment {
		"\(name)": treatment.harness
	}
}

_roleEnabled: {
	for name, role in _roles
	for id, treatment in _treatments
	if id == role.role_treatment {
		"\(name)": treatment.enabled
	}
}

// C-CONFIG-001 — a role reaches a harness whose profile is ruled out.
// Split by reachability rather than waived: deferred while the treatment is
// disabled, hard the moment anyone enables it. A waiver has to be remembered;
// this arms itself.
_cConfig001: {
	for name, harness in _roleHarness
	for id, profile in _harnesses
	if id == harness && profile.version_pin == "ruled-out" && _roleEnabled[name] {
		"\(name)": "role reaches harness '\(harness)', ruled-out in its profile, and its treatment is ENABLED"
	}
}

_deferred001: {
	for name, harness in _roleHarness
	for id, profile in _harnesses
	if id == harness && profile.version_pin == "ruled-out" && !_roleEnabled[name] {
		"\(name)": "role reaches harness '\(harness)', ruled-out in its profile — latent only because its treatment is disabled; resolve before arming"
	}
}

// C-CONFIG-009 — a Role-Treatment id must not encode which vendor serves it.
_cConfig009: {
	for id, treatment in _treatments
	for harness, _ in _harnesses
	if strings.Contains(id, harness) {
		"\(id)": "Role-Treatment id encodes the harness name '\(harness)' — the binding belongs in the harness field"
	}
}

deferred: {
	for subject, reason in _deferred001 {"C-CONFIG-001 \(subject)": reason}
}

diagnostics: {
	for subject, reason in _cConfig001 {"C-CONFIG-001 \(subject)": reason}
	for subject, reason in _cConfig009 {"C-CONFIG-009 \(subject)": reason}
}
