# External closeout

Use this mode only after the local candidate passes and release is separately authorized.

## Candidate manifest

Identify the exact candidate before deployment. Record the repository and branch, commit when present, relevant staged/unstaged/untracked file hashes, expected authored sources, generated outputs, build command and build identity, affected corpus summary/hash, initial dirty-worktree state, and `gitDirty=1` when applicable. A dirty worktree is not automatically a blocker; an unidentified candidate is.

Determine source/generator ownership before editing generated output. Compare the post-build generated diff with the initial worktree, preserve unrelated user changes, and never reset, clean, substitute a clean checkout, or revert unrelated files without an explicit request.

If the candidate changes after acceptance, invalidate the prior acceptance and rerun the declared gate. Deploy exactly the accepted candidate; do not rely only on a moving branch name or mutable alias.

## Release and live receipt

Discover the actual deployment path and verify the target environment. Record release authorization, candidate identity, deployment ID, immutable build/artifact identity, production alias, start/completion times, errors, rollback path, and the live-verification report. Match the verification universe to the approved change universe.

If release is not authorized, return the accepted candidate and the exact closeout blocker. If provider mutation is not authorized, stop after live verification and name it separately. Later authorization resumes this chain; it does not erase the existing evidence or require a new audit unless the candidate or evidence materially changed.
