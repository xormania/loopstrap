package contract

// The vendor boundary.
//
// spec/cue proves that documents are coherent. It cannot prove that a vendor
// binary accepts the flags a profile passes it — that is a claim about someone
// else's program. The nearest checkable thing is a SNAPSHOT of the command-line
// surface, and then unification does the rest: a profile's argv is the declared
// side, the snapshot is the extracted side, and disagreement is a diagnostic
// before a launch rather than a rejection during one.
//
// An earlier generation of this system solved this by grepping the vendor's
// --help output inside the launcher, pinned to one version, at launch time. This
// moves the same check to gate time and makes its provenance explicit.

import (
	"list"
	"strings"
)

_cliHarnesses: configs["harness-cli"].data.harnesses
_profileHarnesses: configs["harness-profiles"].data.harnesses

// Flags a profile actually passes, per harness.
_profileFlags: {
	for name, profile in _profileHarnesses {
		"\(name)": list.Concat([
			[for token in profile.argv if strings.HasPrefix(token, "-") && token != "-" {token}],
			[if profile.smoke_argv != _|_ for token in profile.smoke_argv if strings.HasPrefix(token, "-") && token != "-" {token}],
		])
	}
}

// C-CLI-001 — a profile passes a flag the snapshot does not declare.
// This is the drift that used to surface as a vendor rejecting an argument
// mid-run, after the tokens were spent.
_cCli001: {
	for name, flags in _profileFlags
	if (_cliHarnesses & {"\(name)": _}) != _|_
	for cliName, cli in _cliHarnesses
	if cliName == name
	let declared = [for flag in cli.flags {flag.name}]
	for flag in flags
	if !list.Contains(declared, flag) {
		"\(name) \(flag)": "profile passes '\(flag)', which the harness CLI snapshot does not declare"
	}
}

// C-CLI-002 — a profile has no CLI snapshot at all.
_cCli002: {
	for name, _ in _profileHarnesses
	let hits = [for cliName, _ in _cliHarnesses if cliName == name {cliName}]
	if len(hits) != 1 {
		"\(name)": "harness profile exists but its command-line surface has never been recorded"
	}
}

// C-CLI-003 — the snapshot and the profile disagree about the pinned version.
// Two files naming the same version is exactly the drift that goes unnoticed.
_cCli003: {
	for name, profile in _profileHarnesses
	for cliName, cli in _cliHarnesses
	if cliName == name && cli.version != profile.version_pin {
		"\(name)": "CLI snapshot records version '\(cli.version)' but the profile pins '\(profile.version_pin)'"
	}
}

// C-CLI-004 — a probed snapshot must carry the evidence of having been probed.
_cCli004: {
	for name, cli in _cliHarnesses
	if cli.provenance == "probed" && (cli.probed_at == null || cli.binary_sha256 == null) {
		"\(name)": "snapshot claims provenance 'probed' but carries no probed_at or binary_sha256"
	}
}

// C-CLI-005 — a treatment may not be ENABLED against a surface nobody has asked
// the binary about. Deferred while everything is disabled, hard the moment one
// is enabled: the same self-arming shape as C-CONFIG-001, because the cost of
// being wrong is only paid at launch.
_cCli005: {
	for name, harness in _roleHarness
	for cliName, cli in _cliHarnesses
	if cliName == harness && cli.provenance != "probed" && _roleEnabled[name] {
		"\(name)": "role is ENABLED against harness '\(harness)', whose CLI surface is only declared — probe it before arming"
	}
}

_deferredCli005: {
	for name, harness in _roleHarness
	for cliName, cli in _cliHarnesses
	if cliName == harness && cli.provenance != "probed" && !_roleEnabled[name] {
		"\(name)": "harness '\(harness)' CLI surface is declared, never probed — nobody has asked the binary what it accepts; latent only because the treatment is disabled"
	}
}
