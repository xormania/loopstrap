package project

project: contracts: items: [{
	id:            "contract.root"
	title:         "Analyze a document"
	preconditions: ["A document is available."]
	guarantees: [{
		id:                "guarantee.root"
		statement:         "The application produces analysis for the document."
		term_refs:         ["term.document"]
		verification_refs: ["verify.root"]
	}]
	invariants: ["The document version remains identifiable."]
	failures:   ["Invalid input is reported without a false success."]
	responsibilities: [{
		subject: "application"
		duty:    "Produce analysis."
	}]
	verification: [{
		id:       "verify.root"
		kind:     "system_test"
		required: true
	}]
}]
