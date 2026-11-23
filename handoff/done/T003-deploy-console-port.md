Allowed: sites/scheduler-dashboard/, docs/INTEGRATION_VALIDATION.md, handoff/
Time box: 30

## Goal
Deploy the Site rebuilt as a direct port of the Foreman console (same menu, pages, content and styling), and capture evidence.

## Context
worker/page.html, app.txt, style.css and dist/ were rebuilt by Claude (build, validate, 9/9 tests pass; also rendered locally in headless Chrome under the same CSP). The UI is now the console with sample data labeled "Sample data": menu Overview / Projects / Harness map / Loops and checks / Models and keys / Usage and cost / New project, plus the PROJECTS list (Koboo, Oppo, Compass, sample). The page is pixel-identical to the console at 1280 px wide for all seven menu entries (verified by screenshot diff in headless Chrome). The live feed UI is hidden; only the owner session check and sign-in remain. Inline style attributes are re-applied through the CSSOM because the CSP forbids inline styles; the CSP header is unchanged and browser console CSP warnings for style attributes are expected.
Source files for the console code are in handoff/build-src/ (do not deploy from there).

## Constraints
Keep REMOTE_CONTROL_ENABLED=false, the owner-only audience, the read-only bypass and the CSP unchanged. Do not edit worker files except to fix a build or test failure; report any fix. Ignore sites/scheduler-dashboard/_to_delete.

## Done when
1. npm run build, validate and test pass on your checkout.
2. Pushed, saved as version 12, deployed privately; version and deployment ID in docs/INTEGRATION_VALIDATION.md.
3. Signed in as the owner: screenshots (desktop 1280 wide, plus Overview at 390 wide) of every menu entry, the New project wizard steps 1 to 5, a role click on Harness map. Save under handoff/results/evidence/T003/ with the visible text of each.
4. Report any browser console errors other than the CSP style-attribute warnings.
5. Result file at handoff/results/T003.result.md.
Claude checks (not Codex): side-by-side comparison with the console.
