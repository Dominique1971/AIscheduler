# Scheduler project intake v1

Project ID: dummy-markdown-sample-2
Project name: Second Markdown sample plan
Repository path: ./runtime/examples/dummy-markdown-sample-2
Base branch: main
Maximum workers: 2

## Description
Plan a synthetic sample report. Simulation receipts illustrate task order; they do not create the described report.

## Tasks

### source: Specify sample input
Description: Define the sample records and fields for the report.
Estimate minutes: 3
Depends on: none
Acceptance criteria:
- The sample fields and record count are stated.

### check: Specify quality checks
Description: Define checks for missing and out-of-range sample values.
Estimate minutes: 2
Depends on: source
Acceptance criteria:
- Missing-value and range rules are documented.

### summarize: Specify summary
Description: Define how the sample records would be grouped and summarized.
Estimate minutes: 4
Depends on: source
Acceptance criteria:
- The summary calculation is unambiguous.

### review: Review report outline
Description: Combine the quality and summary specifications into a report outline.
Estimate minutes: 3
Depends on: check, summarize
Acceptance criteria:
- The outline references both preceding specifications.
