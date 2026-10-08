# Registered instruction continuity / 注册命令连续性合同

The current host interprets direct human speech, including explicit corrections, rhetorical emphasis, duplicates and endorsed AI drafts. This module verifies provenance and revision transitions; it is not an NLP model.

- `command_status`: read an existing Task's complete command list and states.
- `command_update`: owner-authorized bounded update; `task_id`, exact `expected_revision`,1–30 entries. Each entry has key, interpreted text, exact source quote/ref, interpretation_basis, kind and state. Current direct-user source and attestation are required for executable entries. Historical/tool/AI-only sources cannot authorize instructions. Explicit correction is required to change text or cancel an old entry. Completion requires fresh result evidence.100-entry overflow fails explicitly rather than evicting commands.
- Context: all active entries form a mandatory lane. Source revision change invalidates preparation; optional recall cannot evict commands. After compaction, call the current mapped Task context again. Native automatic callback coverage is separately evidenced.
- Registered delivery rejects unsatisfied actionable instructions and still requires existing registered validation. It does not intercept arbitrary host tools or ordinary prose completion claims.

## Finite retry gateway

`guard_probe` and `guard_reprepare` require an explicit Task retry_guard with enabled=true, exact read_paths and bounded max_same_experiment1–10. Probe reads only declared local files up to262144 bytes and returns bounded text. Identity excludes changing descriptions/timeouts; it does not infer semantically identical errors. Persisted limits stop another registered attempt. Reprepare returns real structure text plus mandatory commands and requires a correction basis. It proves delivery, not private understanding. No arbitrary shell/model/network action is replayed.

## Human opinions

`learning_opinions` is an owner-authorized bounded read projection of explicit reviewed principle links and actual conditions. Independent and insufficient pairs are not folded into principles. `learning_opinion_source` checks exact case/card identity and returns local source locators/quotes and conditions. It does not read raw attachments or certify domain truth. Empty stores have zero sources. UI and synthetic positive/negative tests accompany the module.

Mutations use the authenticated State Service, operation_id and expected_revision. Public source never includes private input cases or host binding IDs. No new executable FailurePattern is inferred from candidate counts.
