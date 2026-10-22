# Resolve a concrete implementation failure

Reproduce the actual failing condition with the narrowest useful observation. Trace the relevant input, interface and state transition before editing. Check current project entry points and source rather than relying on a stale summary.

State a testable cause and change the affected mechanism. Do not add fallback branches merely to hide a failure or repeatedly make the same unsuccessful experiment. A tool failure is not permission to change model, budget, project or output location.

Verify the changed behavior and a meaningful negative case where necessary. Use existing tests when they cover it; do not add tests that merely restate a trivial reversible edit. Broaden verification when a changed interface, regression or unresolved concern warrants it. Preserve unrelated changes and known-good assets.

This is locally adapted guidance informed by Superpowers systematic debugging; it does not install its complete workflow or mandate worktrees, commits or extra agents.
