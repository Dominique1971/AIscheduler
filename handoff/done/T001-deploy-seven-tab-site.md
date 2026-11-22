Allowed: sites/scheduler-dashboard/, docs/INTEGRATION_VALIDATION.md, handoff/
Time box: 30

## Goal
Deploy the seven-tab Foreman layout to the existing private scheduler Site and capture evidence of the live pages.

## Context
worker/page.html, app.txt, style.css and dist/ are already rebuilt (build, validate, 9/9 tests pass). Live Site is currently version 9 (three tabs).

## Constraints
Keep REMOTE_CONTROL_ENABLED=false, the owner-only audience and the read-only bypass unchanged. Ignore sites/scheduler-dashboard/_to_delete.

## Done when
1. npm run build, validate and test pass.
2. Pushed to the Sites source repository, saved as version 10, deployed privately.
3. Version and deployment ID recorded in docs/INTEGRATION_VALIDATION.md.
4. Signed in as the owner, each of the seven tabs on https://autonomous-scheduler.jetpack71.chatgpt.site opened; visible text and a screenshot per tab saved under handoff/results/evidence/T001/.
5. Result file written to handoff/results/T001.result.md.
Claude checks (not Codex): visual comparison against the Foreman console.
