package project

project: lexicon: {
	entries: [{
		id:               "term.document"
		term:             "document"
		definition:       "A versioned text item analyzed by the target application."
		anti_definitions: ["A Loopstrap Cell."]
		status:           "settled"
	}]
	external_authorities: [{
		id:      "external.lsp"
		name:    "Language Server Protocol"
		uri:     "https://microsoft.github.io/language-server-protocol/"
		version: "3.17"
	}]
}
