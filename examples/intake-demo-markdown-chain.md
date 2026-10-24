# Scheduler project intake v1

Project ID: dummy-markdown-chain-4
Project name: Sequential and branching sample
Repository path: ./runtime/examples/dummy-markdown-chain-4
Base branch: main
Maximum workers: 2

## Description
Describe a synthetic data quality handoff. Simulation records scheduling receipts but does not create or validate a real data product.

## Tasks

### collect: Specify sample records
Description: Identify the synthetic fields and record count.
Estimate minutes: 2
Depends on: none
Acceptance criteria:
- Fields and record count are stated.

### validate: Specify validation rules
Description: Write checks for required and numeric fields.
Estimate minutes: 4
Depends on: collect
Acceptance criteria:
- Required-field and numeric bounds are explicit.

### report: Specify quality report
Description: Define a quality summary using the validation rules.
Estimate minutes: 3
Depends on: validate
Acceptance criteria:
- Every rule has a reported count.

### alert: Specify alert thresholds
Description: Define thresholds for the same validation rules.
Estimate minutes: 2
Depends on: validate
Acceptance criteria:
- Every alert threshold names a validation rule.

### handoff: Review data handoff
Description: Combine the quality report and alert thresholds in a handoff checklist.
Estimate minutes: 2
Depends on: report, alert
Acceptance criteria:
- The checklist references both preceding specifications.
