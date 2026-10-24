# Scheduler project intake v1

Project ID: dummy-import-example
Project name: Example quality review
Repository path: ./runtime/examples/dummy-import-example
Base branch: main
Maximum workers: 2

## Description
Describe a synthetic quality review from sample records through a final handoff. Simulation receipts show scheduling order; they do not create a report.

## Tasks

### records: Specify sample records
Description: Define synthetic fields and example values.
Estimate minutes: 3
Depends on: none
Acceptance criteria:
- Every synthetic field has a name and example value.

### checklist: Specify review checklist
Description: Define independent review questions for the final handoff.
Estimate minutes: 2
Depends on: none
Acceptance criteria:
- Each review question has a pass condition.

### rules: Specify validation rules
Description: Define checks for missing and out-of-range records.
Estimate minutes: 4
Depends on: records
Acceptance criteria:
- Missing and out-of-range cases have explicit rules.

### summary: Specify quality summary
Description: Define counts grouped by validation outcome.
Estimate minutes: 3
Depends on: records, rules
Acceptance criteria:
- Each validation outcome has a reported count.

### handoff: Review handoff
Description: Combine the quality summary and independent checklist.
Estimate minutes: 2
Depends on: summary, checklist
Acceptance criteria:
- The handoff references both the summary and checklist.
