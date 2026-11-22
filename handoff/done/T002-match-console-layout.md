Allowed: sites/scheduler-dashboard/, docs/INTEGRATION_VALIDATION.md, handoff/
Time box: 30

## Goal
Deploy the updated Site layout (metal left rail with large gear logo, menu Overview / Projects / Harness map / Loops and checks / Models and keys / Usage and cost / New project, then a PROJECTS list with status dots and done/total; topbar breadcrumb; favicon; whole-page scroll; KPI cards; progress bars; "Needs attention" list) with the console look: eyebrow + large Impact page titles, glass cards in metal corner brackets, KPI cards, pills and tables. Capture evidence.

## Context
Claude changed worker/page.html, app.txt, style.css, index.js (new owner-gated /icon.svg route), icon.svg and scripts/build.mjs (.svg loader). dist is rebuilt; build, validate and 9/9 tests pass in Claude's copy. Live Site is version 10.

## Constraints
Keep REMOTE_CONTROL_ENABLED=false, the owner-only audience and the read-only bypass unchanged. Do not edit worker files except to fix a build or test failure, and report any such fix. Ignore sites/scheduler-dashboard/_to_delete.

## Done when
1. npm run build, validate and test pass on your checkout.
2. Pushed, saved as version 11, deployed privately; version and deployment ID recorded in docs/INTEGRATION_VALIDATION.md.
3. Signed in as the owner: confirm /icon.svg loads (status 200 for the owner) and the tab icon shows. Screenshots and visible text for all seven menu entries and one project entry from the rail, at desktop width and at about 390 px width, saved under handoff/results/evidence/T002/. Also a full-page screenshot of #harness and #loops showing the whole page scrolls and no diagram is cut off.
4. Report whether the outbound bridge can be started now using its documented procedure, without changing configuration, keys or the audience. If yes, start it, wait for one update, and capture #overall again showing fresh data. If not, say why.
5. Result file at handoff/results/T002.result.md.
Claude checks (not Codex): visual comparison against the Foreman console.
