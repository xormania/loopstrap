package project

import "list"

#Status: "settled" | "proposed" | "open" | "retired"
#ID: =~"^[a-z][a-z0-9]*(\\.[a-z0-9][a-z0-9_-]*)+$"
#Digest: =~"^sha256:[0-9a-f]{64}$"

#LexiconEntry: close({
	id:               #ID
	term:             string & !=""
	definition:       string & !=""
	anti_definitions: [string & !="", ...string]
	status:           #Status
})

#ExternalAuthority: close({
	id:      #ID
	name:    string & !=""
	uri:     =~"^https?://"
	version: string & !=""
})

#Guarantee: close({
	id:                #ID
	statement:         string & !=""
	term_refs:         [#ID, ...#ID]
	verification_refs: [#ID, ...#ID]
})

#Verification: close({
	id:       #ID
	kind:     "unit_test" | "integration_test" | "system_test" | "inspection" | "measurement"
	required: bool
})

#DesignContract: close({
	id:            #ID
	title:         string & !=""
	preconditions: [string & !="", ...string]
	guarantees:    [#Guarantee, ...#Guarantee]
	invariants:    [string & !="", ...string]
	failures:      [string & !="", ...string]
	responsibilities: [{
		subject: string & !=""
		duty:    string & !=""
	}, ...{
		subject: string & !=""
		duty:    string & !=""
	}]
	verification: [#Verification, ...#Verification]

	_uniqueGuarantees: list.UniqueItems([for item in guarantees {item.id}]) & true
	_uniqueVerification: list.UniqueItems([for item in verification {item.id}]) & true
})

#LanguageSelection: close({
	name:    string & !=""
	version: string & !=""
	status:  #Status
})

#ProjectPackage: close({
	format_version: "loopstrap.project/v1"
	project: close({
		id:     =~"^[a-z][a-z0-9-]*$"
		name:   string & !=""
		status: #Status
	})
	lexicon: close({
		entries:              [#LexiconEntry, ...#LexiconEntry]
		external_authorities: [#ExternalAuthority, ...#ExternalAuthority]
	})
	contracts: close({
		items: [#DesignContract, ...#DesignContract]
	})
	realization: close({
		languages: [#LanguageSelection, ...#LanguageSelection]
		platforms: [string & !="", ...string]
		commands: close({
			build: [string & !="", ...string]
			test:  [string & !="", ...string]
		})
		standards: [#ID, ...#ID]
		dependencies: close({
			policy: "allowlisted" | "denylisted" | "unconstrained"
			items:  [...string]
		})
		packaging:         [string & !="", ...string]
		license:           string & !=""
		delegated_choices: [...string]
	})

	_uniqueTerms:      list.UniqueItems([for item in lexicon.entries {item.id}]) & true
	_uniqueAuthorities: list.UniqueItems([for item in lexicon.external_authorities {item.id}]) & true
	_uniqueContracts:  list.UniqueItems([for item in contracts.items {item.id}]) & true

	_termIDs: {
		for item in lexicon.entries {
			"\(item.id)": true
		}
	}
	_authorityIDs: {
		for item in lexicon.external_authorities {
			"\(item.id)": true
		}
	}
	_verificationIDs: {
		for contract in contracts.items {
			"\(contract.id)": {
				for item in contract.verification {
					"\(item.id)": true
				}
			}
		}
	}
	_termReferenceChecks: {
		for contract in contracts.items {
			"\(contract.id)": {
				for guarantee in contract.guarantees {
					"\(guarantee.id)": [
						for reference in guarantee.term_refs {
							_termIDs[reference]
						},
					]
				}
			}
		}
	}
	_verificationReferenceChecks: {
		for contract in contracts.items {
			"\(contract.id)": {
				for guarantee in contract.guarantees {
					"\(guarantee.id)": [
						for reference in guarantee.verification_refs {
							_verificationIDs[contract.id][reference]
						},
					]
				}
			}
		}
	}
	_standardReferenceChecks: [
		for reference in realization.standards {
			_authorityIDs[reference]
		},
	]
})
