package contract

// Shape of the normalized facts produced by
// artifacts/instance/tools/schema-facts.py. Facts only: nothing here declares
// intent or reaches a verdict.
//
// This package is DEV-LANE. It is never loaded by loopstrap_core, never shipped
// in spec/cue/, and uses its own package name so a development expectation can
// never unify into the production contract surface.

#PythonFact: close({
	kind:   "class_fields" | "exact_call"
	module: string & !=""
	symbol: string & !=""
	label:  string & !=""
	fields: [string, ...string]
})

#UnresolvedSite: close({
	module: string & !=""
	line:   int & >=1
	label:  string | null
	reason: string & !=""
})

#CueFact: close({
	definition: =~"^#\\w+$"
	file:       string & !=""
	fields: [string, ...string]
})

python: [...#PythonFact]
pythonUnresolved: [...#UnresolvedSite]
cue: [...#CueFact]
