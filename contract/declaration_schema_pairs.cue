package contract

// Contract-authoritative declaration: which Python exact-field set describes the
// same document as which CUE definition.
//
// This cannot be inferred. `EvidenceRecord.FIELDS` matching `#EvidenceRecord` is
// a naming coincidence; `_exact(data, {...}, "port contract")` matching `#Port`
// is not a coincidence and not a name match either. Pairing is intent, so it is
// declared here and checked, never guessed by the extractor.
//
// Adding a document type to one language and not the other is caught by
// C-SCHEMA-002, so this file cannot silently fall behind either side.

#Pair: close({
	// The `label` field of a Python fact: the third argument to _exact(), or the
	// class name for a FIELDS attribute.
	pythonLabel: string & !=""
	// The CUE definition, exactly as written including the leading '#'.
	definition: =~"^#\\w+$"
	// Field names CUE marks optional and Python therefore admits but does not
	// require. `cue eval` omits optional fields from its enumeration, so these
	// are named here to document the asymmetry rather than to hide it.
	optional: [...string]
	why: string & !=""
})

pairs: [...#Pair] & [
	{
		pythonLabel: "EvidenceRecord"
		definition:  "#EvidenceRecord"
		optional: []
		why: "EvidenceCompiler validates with CUE then constructs with from_dict, both over one document; a divergence made acceptance-check unsatisfiable for a week."
	},
	{
		pythonLabel: "AcceptanceObligation"
		definition:  "#AcceptanceObligation"
		optional: []
		why: "Obligations arrive inside the same acceptance request and cross the same bridge."
	},
	{
		pythonLabel: "acceptance request"
		definition:  "#AcceptanceRequest"
		optional: []
		why: "The document the acceptance-check subcommand accepts on stdin."
	},
	{
		pythonLabel: "acceptance record"
		definition:  "#AcceptanceRecord"
		optional: []
		why: "The document the acceptance-check subcommand emits."
	},
	{
		pythonLabel: "contract graph"
		definition:  "#ContractGraph"
		optional: []
		why: "The document the plan-check subcommand accepts."
	},
	{
		pythonLabel: "Cell contract"
		definition:  "#CellContract"
		optional: []
		why: "Nested inside every contract graph."
	},
	{
		pythonLabel: "composite Cell contract"
		definition:  "#CompositeContract"
		optional: ["cell_id"]
		why: "contracts.py admits cell_id as an optional extra; CUE marks it cell_id? and cue eval omits optional fields, so both sides agree on the required set."
	},
	{
		pythonLabel: "port contract"
		definition:  "#Port"
		optional: []
		why: "Port schema references are what connection unification compares."
	},
	{
		pythonLabel: "port reference"
		definition:  "#PortReference"
		optional: []
		why: "Names the endpoint of a connection."
	},
	{
		pythonLabel: "connection contract"
		definition:  "#Connection"
		optional: []
		why: "The edge whose endpoint schemas must unify."
	},
	{
		pythonLabel: "verification obligation"
		definition:  "#VerificationObligation"
		optional: []
		why: "Carried by both cells and composites."
	},
	{
		pythonLabel: "guarantee contract"
		definition:  "#MemberGuarantee"
		optional: []
		why: "contracts.py validates member guarantees under this label; composite guarantees carry an extra supported_by and are checked by #CompositeGuarantee through the graph, not by this call site."
	},
]

// Python exact-field sets with no CUE counterpart, declared deliberately so that
// C-SCHEMA-002 can distinguish 'not paired yet' from 'never crosses the bridge'.
unpaired: [...close({label: string & !="", why: string & !=""})] & [
	{label: "CertificationContract", why: "Certification input is Python-side configuration; no CUE definition exists or is intended."},
	{label: "CertificationReceipt", why: "Receipt is produced and consumed inside the kernel and never validated by CUE."},
	{label: "RoleTreatment", why: "Loaded from config JSON, not from a CUE-validated document."},
	{label: "LaunchAttestation", why: "Wrapper-owned runtime record; never crosses the CUE bridge."},
	{label: "mechanical obligation", why: "Certification-internal."},
	{label: "inference task", why: "Certification-internal."},
	{label: "executable identity", why: "Certification-internal."},
	{label: "mechanical observation", why: "Certification-internal."},
	{label: "inference observation", why: "Certification-internal."},
	{label: "inference call", why: "Certification-internal."},
	{label: "mutation evidence", why: "Certification-internal."},
	{label: "child Cell", why: "Driver-internal scripted result parsing."},
	{label: "contract", why: "Driver-internal phase result."},
	{label: "tests", why: "Driver-internal phase result."},
	{label: "plan", why: "Driver-internal phase result."},
	{label: "implementation", why: "Driver-internal phase result."},
	{label: "integration", why: "Driver-internal phase result."},
	{label: "post-review", why: "Driver-internal phase result."},
]

// _exact() call sites whose field set is not a resolvable literal. Each is named
// so that a NEW unresolvable site is a diagnostic rather than silent erosion of
// what the extractor can see.
waivedUnresolved: [...close({module: string & !="", label: string & !="", why: string & !=""})] & [
	{module: "certification.py", label: "Loopstrap conformance observation", why: "Field set is computed from the conformance spec at call time; certification suite owns this behaviorally."},
	{module: "driver.py", label: "pre-review", why: "Field set varies with the configured phase role; driver suite owns this behaviorally."},
]
