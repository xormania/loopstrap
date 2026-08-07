package contract

// The probe deliverable's contract.
//
// probe/run.sh interrogates a vendor CLI and writes two files: a markdown fact
// sheet for a human, and one JSON object for this. The markdown is never parsed.
// A probe result enters the system only by satisfying #HarnessSurface, so the
// prompt's example is a hint and THIS is the authority — if they disagree, the
// prompt is wrong.
//
// Closed on purpose. An unexpected field is a probe that answered a question
// nobody asked, and silently absorbing it is how a snapshot starts carrying
// unvalidated claims.

import "list"

#Sha256: =~"^[0-9a-f]{64}$"
#Rfc3339: =~"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]+)?Z$"

// How a fact was obtained, weakest last. Never upgrade a tag you did not earn:
// "probed" means the binary was run and the behaviour observed, and it is the
// only tag that licenses arming a treatment.
#Evidence: "probed" | "docs" | "derived"

#Flag: close({
	name!:        =~"^-{1,2}[A-Za-z0-9][A-Za-z0-9-]*$"
	takes_value!: bool
	status!:      #Evidence
	// Free text from the probe. Not interpreted, kept so a reader can see why a
	// flag was tagged the way it was.
	note?: string
})

#HarnessSurface: close({
	schema!:  "loopstrap.harness-surface/v1"
	harness!: string & !=""
	version!: string & !=""

	binary_path!:   string | null
	binary_sha256!: #Sha256 | null
	probed_at!:     #Rfc3339 | null

	flags!: [#Flag, ...#Flag]

	// A flag can only be claimed once.
	_uniqueFlags: list.UniqueItems([for flag in flags {flag.name}]) & true

	// Evidence rule. If the probe claims to have run the binary for even one
	// flag, it must carry the evidence of having done so. This is what stops a
	// surface from being upgraded to "probed" by assertion — the same reason
	// C-CLI-004 exists on the ingested side.
	_probedNeedsEvidence: {
		let probed = [for flag in flags if flag.status == "probed" {flag.name}]
		if len(probed) > 0 {
			evidence: binary_sha256 & #Sha256
			stamped:  probed_at & #Rfc3339
		}
	}
})
