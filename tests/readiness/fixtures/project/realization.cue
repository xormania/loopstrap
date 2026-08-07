package project

project: realization: {
	languages: [{
		name:    "rust"
		version: "1.90"
		status:  "settled"
	}]
	platforms: ["linux"]
	commands: {
		build: ["cargo", "build"]
		test:  ["cargo", "test"]
	}
	standards: ["external.lsp"]
	dependencies: {
		policy: "allowlisted"
		items:  []
	}
	packaging:         ["binary"]
	license:           "Apache-2.0"
	delegated_choices: []
}
