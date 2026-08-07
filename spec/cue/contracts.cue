package contracts

import "list"

#Nonempty: string & !=""
#Digest: =~"^sha256:[0-9a-f]{64}$"
#Responsibility: "exclusive" | "shared" | "supporting" | "composite"

#Port: close({
	id:         #Nonempty
	schema_ref: #Nonempty
})

#VerificationObligation: close({
	id:                        #Nonempty
	scope_kind:                "cell" | "composite" | "root"
	eligible_producer_classes: [#Nonempty, ...#Nonempty]
	minimum_evidence:          int & >=1
})

#MemberGuarantee: close({
	id:                          #Nonempty
	responsibility:              "exclusive" | "shared" | "supporting"
	contract_refs:               [#Nonempty, ...#Nonempty]
	verification_obligation_ids: [#Nonempty, ...#Nonempty]
})

#CompositeGuarantee: close({
	id:                          #Nonempty
	responsibility:              "composite"
	contract_refs:               [#Nonempty, ...#Nonempty]
	verification_obligation_ids: [#Nonempty, ...#Nonempty]
	supported_by:                [...#Nonempty]
})

#CellContract: close({
	id:                       #Nonempty
	contract_refs:            [#Nonempty, ...#Nonempty]
	inputs:                   [#Port, ...#Port]
	outputs:                  [#Port, ...#Port]
	guarantees:               [#MemberGuarantee, ...#MemberGuarantee]
	failures:                 [#Nonempty, ...#Nonempty]
	owned_effects:            [#Nonempty, ...#Nonempty]
	dependencies:             [...#Nonempty]
	invariants:               [#Nonempty, ...#Nonempty]
	verification_obligations: [#VerificationObligation, ...#VerificationObligation]

	_uniqueInputs:      list.UniqueItems([for item in inputs {item.id}]) & true
	_uniqueOutputs:     list.UniqueItems([for item in outputs {item.id}]) & true
	_uniqueGuarantees:  list.UniqueItems([for item in guarantees {item.id}]) & true
	_uniqueVerification: list.UniqueItems([for item in verification_obligations {item.id}]) & true
})

#PortReference: close({
	cell_id: #Nonempty
	port_id: #Nonempty
})

#Connection: close({
	source: #PortReference
	target: #PortReference
})

#CompositeContract: close({
	id:                       #Nonempty
	cell_id?:                 #Nonempty
	members:                  [#Nonempty, ...#Nonempty]
	connections:              [#Connection, ...#Connection]
	external_inputs:          [#PortReference, ...#PortReference]
	external_outputs:         [#PortReference, ...#PortReference]
	guarantees:               [#CompositeGuarantee, ...#CompositeGuarantee]
	failures:                 [#Nonempty, ...#Nonempty]
	invariants:               [#Nonempty, ...#Nonempty]
	verification_obligations: [#VerificationObligation, ...#VerificationObligation]

	_uniqueMembers:      list.UniqueItems(members) & true
	_uniqueGuarantees:   list.UniqueItems([for item in guarantees {item.id}]) & true
	_uniqueVerification: list.UniqueItems([for item in verification_obligations {item.id}]) & true
})

#ContractGraph: close({
	version:              int & >=1
	specification_digest: #Digest
	root_composite_id:    #Nonempty
	cells:                [#CellContract, ...#CellContract]
	composites:           [#CompositeContract, ...#CompositeContract]

	_uniqueCells:      list.UniqueItems([for item in cells {item.id}]) & true
	_uniqueComposites: list.UniqueItems([for item in composites {item.id}]) & true

	_cellByID: {
		for cell in cells {
			"\(cell.id)": cell
		}
	}
	_compositeByID: {
		for composite in composites {
			"\(composite.id)": composite
		}
	}
	_rootCheck: _compositeByID[root_composite_id].id

	_inputByCell: {
		for cell in cells {
			"\(cell.id)": {
				for port in cell.inputs {
					"\(port.id)": port
				}
			}
		}
	}
	_outputByCell: {
		for cell in cells {
			"\(cell.id)": {
				for port in cell.outputs {
					"\(port.id)": port
				}
			}
		}
	}
	// A Cell may only depend on a Cell the graph declares. Resolving each
	// referent through _cellByID makes an undeclared one an undefined field.
	// Containment acyclicity is not expressible here without a declared depth
	// bound, and stays a Python-side check.
	_dependencyChecks: {
		for cell in cells {
			"\(cell.id)": {
				for index, dependency in cell.dependencies {
					"\(index)": _cellByID[dependency].id
				}
			}
		}
	}
	// A composite naming cell_id is the interior of that Cell, and a parent wires
	// the Cell by the Cell's declared ports. The interior must therefore expose
	// exactly those port schemas, positionally — list unification requires equal
	// length and equal elements, so both subsetting directions are refused.
	// Iterating the composite's own fields tests cell_id's presence without an
	// existence operator.
	_interiorBoundaries: {
		for composite in composites
		for key, controlling in composite
		if key == "cell_id" {
			"\(composite.id)": {
				inputs: [for reference in composite.external_inputs {
					_inputByCell[reference.cell_id][reference.port_id].schema_ref
				}] & [for port in _cellByID[controlling].inputs {port.schema_ref}]
				outputs: [for reference in composite.external_outputs {
					_outputByCell[reference.cell_id][reference.port_id].schema_ref
				}] & [for port in _cellByID[controlling].outputs {port.schema_ref}]
			}
		}
	}
	_connectionChecks: {
		for composite in composites {
			"\(composite.id)": {
				for index, connection in composite.connections {
					"\(index)": {
						sourceMember: _cellByID[connection.source.cell_id].id
						targetMember: _cellByID[connection.target.cell_id].id
						schema: _outputByCell[connection.source.cell_id][connection.source.port_id].schema_ref &
							_inputByCell[connection.target.cell_id][connection.target.port_id].schema_ref
					}
				}
			}
		}
	}
})
