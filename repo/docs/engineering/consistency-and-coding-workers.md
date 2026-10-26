# Source consistency and coding workers

UACF now separates interpreting a request, reviewing that interpretation,
executing a coding unit, and reviewing the resulting implementation. Structural
validation does not prove that a model understands Chinese or English correctly.

## Consistency loop

The main host registers the complete original Message, then calls the existing
authenticated State service actions `consistency_prepare`, `consistency_review`
and `consistency_deliver`. Each action binds the exact Task revision. Read-only
`consistency_status` is also exposed over MCP.

The contract contains `sources`, complete non-overlapping `clauses` with exact
character spans/quotes, discourse `role`, logical `relation`, `scope`, interpreted
meaning and corresponding command keys. Implementation `decisions` distinguish
explicit requirements, model choices and unresolved matters. Executable numbers
need a referent, metric/denominator, unit and basis. Examples and unresolved numbers
cannot execute; questions, quotations and rhetoric cannot directly authorize work.
The reviewer must also look for omitted numbers and incorrect discourse labels:
mechanically checking declared labels cannot establish their truth.

A separately identified reviewer compares the original source with this contract.
Review evidence must contain the exact public review, or a completed native DS
response with matching contract hash/verdict/findings and original run identity.
Self-review identity, unrelated Evidence and incomplete responses are rejected.
Changed requirements, source revisions or interpretation invalidate review.

Registered implementation/review stages require this review. Registered delivery
also requires a command-by-command trace to current file hashes and actual check
results. Known native edit tools and `git push` pass through the same check when
the installed host calls `work_admit`. New enrolled Tasks require the loop; old
archives are not silently rewritten. Ordinary discussion needs no code workflow.

## Default coding route

| Condition | Default |
|---|---|
| No secondary model configured | Remind at each work start; retain original main model |
| Configured secondary model broken or unverified | Registered DeepSeek |
| Unknown quota, invalid or expired reset | Registered DeepSeek |
| Remaining <40%, **or** remaining percentage points / positive reset minutes <1 | Registered DeepSeek |
| Both thresholds satisfied and native Luna usable | Permit exact native `gpt-6-luna` |

Equality is allowed: 40% with 40 minutes is eligible for Luna. A used percentage
must first be converted to remaining percentage; reset timestamps are Unix seconds,
not minutes. Quota snapshots expire after five minutes. The main host reads native
usage before preparation; absent snapshots conservatively select DS.

Owner action `coding_worker_configure` installs a source-bound future default.
It requires an existing official DSH ProviderProfile. New enrolled Tasks receive
their own RoleAssignment and bounded budget account, not another Task's balance.
The conservative built-in ceiling is 0.1 CNY and at most four calls per new Task;
this is an implementation default, not an Owner-specified constant or an
unlimited spending authorization. Larger jobs need a Task-specific grant.

Use MCP `uacf_coding_worker_prepare` with frozen `interfaces`, `inputs`, `outputs`,
`method`, `boundaries`, `acceptance`, `write_scope`, then
`uacf_coding_worker_run`. DS uses the existing `model_dispatch` → DSH native
generation route. No new direct provider client or provider-key access is added.
Luna returns an exact native `collaboration.spawn_agent` instruction. Record its
public result with `coding_worker_native_result`. Known setup refusal before
generation may use `coding_worker_fallback`; an unknown outcome cannot fall back
or replay. Broken setup persists as DS for the remainder of that Task.

Stable protocol and contract precede the variable work unit. IDs and timestamps
stay in receipts. Record actual input/output/cache tokens, including zero cache
hits; a prefix hash is not a cache-hit guarantee.

The main host reviews the candidate, actual diff, boundaries and actual test
results via `coding_worker_audit`. Candidates never apply or accept themselves.
Incomplete/failed results cannot be accepted. Delivery rejects missing audit,
unresolved calls and changed audited files. The main model retains architecture,
method decisions, ambiguity resolution and final review; delegate bounded chores.

## Enforcement coverage

These are real State/MCP and registered-stage checks, plus known edit/publish
tool admission in hosts with a loaded hook. They are **not** a universal shell,
network or OS interceptor. An existing chat's MCP tool inventory may need refresh;
the authenticated State actions remain available through the existing helper.
DSH/Pi/Codex adapters retain their existing native session architecture. A host
without a loaded hook must be labelled unverified, not universally protected.

Code-only deployment reuses an identical locked Python environment and refuses
changed dependency locks or migrations. It preserves the old deployment pointer
for code rollback and never restores the canonical database.

## Public distribution compatibility

This public distribution preserves the existing private/domain exclusions. When
an installed storage allocator exists, work uses that registered allocator.
Otherwise this registered worker action allocates only under the exact canonical
Owner-selected project root at `.uacf/work/<Task>/coding-workers`; missing roots
are rejected, with no cwd fallback. Domain research work is rejected when its
required research adapter is absent; generic coding does not import that adapter.
No private source quotations, account snapshots, native session bindings or
provider execution receipts are part of the public package.

Publication uses a separate `consistency_publish` preflight trace over the current
code, tests and destination. It is not the final `consistency_deliver` receipt.
Known publish hooks check the preflight; final delivery records the actual remote
result afterward, avoiding a requirement to upload before admitting the upload.

## Resumed tasks and native broker admission

Defaults apply to active resumed Tasks as well as new enrollment. Registered
`coding_worker_bind` repairs the exact current Task; preparation returns the new
`task_ref` when inheritance versions it. Do not silently fall back to main merely
because a configured worker is missing a per-Task binding. Preserve existing
budget-account conflicts and stopped archives. The worker grant includes an
explicit context byte capacity used for complete internal validation, not extra
model-prompt content. The native broker must use that same grant at its second
context check. Confirmed preflight HTTP rejection is zero-cost; transport/unknown
generation outcomes remain reserved and must never be replayed automatically.
The public DSH callback adapter supplies no generation endpoint by itself:
configure an existing authorized native broker and verify its generation path,
or leave secondary models unconfigured and show the normal main-model reminder.

A main audit may quarantine an unknown read-only diagnostic whose output was never
used, allowing unrelated completed work to proceed. It neither accepts a candidate
nor releases the unknown charge or permits replay. Write-capable unknown workers
remain blocked. Each audit is recorded independently; aggregate checks run at delivery.
