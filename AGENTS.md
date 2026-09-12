# Project working agreements

## Git milestones

The repository owner has explicitly requested that completed features and milestones be committed and pushed to GitHub.

- Complete and verify one coherent feature or milestone, update its documentation, then commit and push it before moving to the next milestone.
- Use `origin` (`https://github.com/singhbaidwan/sprout.git`) and the current intended branch; the initial project branch is `main`. Follow any later user instruction to use a different branch or workflow.
- Verify the push succeeded and report the commit and any material validation results. Do not claim that a local commit has been published until the remote confirms it.
- Preserve existing work and remote history. Do not force-push or rewrite published commits unless explicitly requested.
- Keep credentials, environment files, caches, and test outputs out of commits. If a push is blocked by authentication or remote changes, retain the local commit and explain the concrete blocker.

This preference applies to authorized project work; it does not automatically authorize implementing every proposal in the roadmap.

## Implementation and documentation

- Keep the existing game playable while introducing features in small, tested steps.
- Update `docs/DEVELOPMENT_LOG.md` with completed work, decisions, verification, and outstanding work.
- Update the README, requirements, architecture, player guide, or roadmap when behavior or scope changes. Clearly distinguish proposed APIs from implemented ones.
- Run relevant tests before committing. The baseline suite is `python3 -m unittest discover -s tests -v`; HTTP integration tests need temporary loopback sockets.
- Preserve the bounded Python interpreter and local-only server assumptions. New factory mechanics must account for save compatibility and the simulation clock described in `docs/ROADMAP.md`.
