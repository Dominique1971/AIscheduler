# Scheduler project intake v1

Project ID: dummy-markdown-dag-3
Project name: Multi-branch dependency sample
Repository path: ./runtime/examples/dummy-markdown-dag-3
Base branch: main
Maximum workers: 3

## Description
Describe a synthetic publication workflow with two independent starting tasks, a fork, and a three-way join. Simulation completes task receipts without producing a publication.

## Tasks

### source: Specify source records
Description: List fields and provenance for synthetic records.
Estimate minutes: 2
Depends on: none
Acceptance criteria:
- The field list and synthetic provenance are stated.

### assets: Specify illustration assets
Description: List placeholder illustrations independently of the source records.
Estimate minutes: 3
Depends on: none
Acceptance criteria:
- Every placeholder has a name and purpose.

### draft: Specify article outline
Description: Organize the synthetic source records into sections.
Estimate minutes: 5
Depends on: source
Acceptance criteria:
- Each section has an explicit source field.

### audit: Specify record checks
Description: Describe validation checks for the synthetic records.
Estimate minutes: 4
Depends on: source
Acceptance criteria:
- Missing and malformed values have explicit checks.

### captions: Specify captions
Description: Pair illustration placeholders with section captions.
Estimate minutes: 2
Depends on: assets, draft
Acceptance criteria:
- Every placeholder has a matching caption.

### review: Review combined outline
Description: Compare the outline, record checks, and captions.
Estimate minutes: 3
Depends on: draft, audit, captions
Acceptance criteria:
- The review references all three preceding specifications.

### publish: Specify publication handoff
Description: Summarize a handoff checklist for the reviewed synthetic outline.
Estimate minutes: 2
Depends on: review
Acceptance criteria:
- The handoff checklist references the review.
