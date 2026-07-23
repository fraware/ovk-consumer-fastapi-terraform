# Fork PR reduced-permission coverage

## What this consumer automates

`.github/workflows/ovk-fork-simulation.yml` models fork-PR token limits:

- event: `pull_request` (untrusted head checkout semantics)
- permissions: `contents: read` only
- OVK Action pinned to `fraware/open-verification-kernel@v1.2.1`
- `post-comment` / `emit-check` may no-op without write scopes — that is expected

## What we deliberately do not do

- Do **not** use `pull_request_target` with an untrusted checkout. That pattern is a common secret-exfiltration footgun.
- Do **not** claim a true cross-fork human PR has been adjudicated until one is opened from an external fork.

## Remaining human step

1. Fork this repository to a separate GitHub account/org.
2. Open a PR that touches a workflow or app path.
3. Confirm OVK runs with the reduced default `GITHUB_TOKEN` permissions for fork PRs.
4. Record a `human_adjudication` row in `pilot/ledger.json` (not `automated_scenario`).
