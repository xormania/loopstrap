package evidence

import "list"

#Nonempty: string & !=""
#Digest: =~"^sha256:[0-9a-f]{64}$"
#ScopeKind: "cell" | "composite" | "root"

#EvidenceRecord: close({
	id:                   #Nonempty
	specification_digest: #Digest
	cell_id:              #Nonempty
	cell_revision:        int & >=1
	scope_kind:           #ScopeKind
	scope_id:             #Nonempty
	treatment_id:         #Nonempty
	producer_id:          #Nonempty
	producer_class:       #Nonempty
	subject_producer_ids: [#Nonempty, ...#Nonempty]
	obligation_ids:       [#Nonempty, ...#Nonempty]
	execution_ref:        #Digest
	artifact_refs:        [#Digest, ...#Digest]
	observation: {
		[string]: _
	}
	finding_ids: [...#Nonempty]

	_uniqueSubjects:    list.UniqueItems(subject_producer_ids) & true
	_uniqueObligations: list.UniqueItems(obligation_ids) & true
	_uniqueArtifacts:   list.UniqueItems(artifact_refs) & true
	_uniqueFindings:    list.UniqueItems(finding_ids) & true
})

#AcceptanceObligation: close({
	id:                        #Nonempty
	scope_kind:                #ScopeKind
	scope_id:                  #Nonempty
	eligible_producer_classes: [#Nonempty, ...#Nonempty]
	minimum_evidence:          int & >=1
	independent:               bool

	_uniqueClasses: list.UniqueItems(eligible_producer_classes) & true
})

#AcceptanceRequest: close({
	acceptance_id:        #Nonempty
	specification_digest: #Digest
	current_revisions: {
		[#Nonempty]: int & >=1
	}
	obligations:            [#AcceptanceObligation, ...#AcceptanceObligation]
	evidence:               [...#EvidenceRecord]
	unresolved_finding_ids: [...#Nonempty]

	_uniqueObligations: list.UniqueItems([for item in obligations {item.id}]) & true
	_uniqueEvidence:    list.UniqueItems([for item in evidence {item.id}]) & true
	_uniqueFindings:    list.UniqueItems(unresolved_finding_ids) & true
})

#AcceptanceRecord: close({
	id:                         #Nonempty
	specification_digest:       #Digest
	accepted:                   bool
	satisfied_obligation_ids:   [...#Nonempty]
	unsatisfied_obligation_ids: [...#Nonempty]
	qualifying_evidence_ids:    [...#Nonempty]
	unresolved_finding_ids:     [...#Nonempty]
})
