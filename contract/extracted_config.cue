package contract

// Shape of the merged configuration set, produced by
//   cue export --with-context -l '"configs"' -l '<stem>' -l '"data"' config/*.json
// so every config/<name>.v1.json arrives under its own key with no collision —
// four of the seven declare a top-level `version` and two a `config_version`.
//
// Deliberately OPEN (no close()). This describes only the fields the invariants
// join on; each config keeps its own full shape and its own owner. The point is
// to hold all seven in one namespace long enough to ask whether they agree, not
// to restate them.

#Role: {
	role_treatment: string
	requires: [...string]
	...
}

#RoleTreatment: {
	id:      string
	role:    string
	harness: string
	...
}

#Phase: {
	kind: string
	// null where a phase has no role, e.g. `children`, which waits rather than
	// dispatching.
	role: string | null
	on: [string]: string
	...
}

#HarnessProfile: {
	version_pin: string
	...
}

configs: {
	roles: data: {
		roles: [string]: #Role
		independence: [...{role: string, from_role: string, ...}]
		...
	}

	"role-treatments": data: {
		role_treatments: [...#RoleTreatment]
		...
	}

	"harness-profiles": data: {
		harnesses: [string]: #HarnessProfile
		...
	}

	workflow: data: {
		initial: string
		phases: [string]: #Phase
		...
	}

	// Present in the merged document and not joined on by any invariant yet.
	"cue-tool": data: {...}
	"harness-certification": data: {...}
	seal: data: {...}
}
