# UACF complete system design and operating model

Revision 2, 7 October 2026. This is a full English description, rather than an English abstract. Implementation, installation, invocation and acceptance are separate claims. A complete specification does not imply that every deployment has passed every acceptance check.

## Purpose and intended users

UACF, the Unified Agentic Continuity Fabric, supports continuing AI-assisted work. A research project, a writing task, a video production and an engineering task all need a reliable account of what the user requested, what was done, what changed, where results came from and what remains unresolved. UACF connects these records with relevant historical lessons and bounded acceptance checks.

The execution host still performs reasoning and tools. Ordinary work uses the current host. DeepSeek is an explicitly selected external route, subject to its own authorization and budget. UACF neither replaces the model nor promises that possessing a failure notebook prevents every future mistake. It does not inspect or verify private reasoning.

Nontechnical users should start with the Chinese or English user guide and the supplied launcher. The permanent UI exposes tasks, work updates, knowledge, issues, source conditions, review status and costs. Programming interfaces support integration, but they are not the only intended user experience.

## Architecture and authority

The UI is a readable projection of canonical objects. The control plane assembles current Task contracts, response requirements, execution roles, permission boundaries, learning candidates and acceptance obligations. Storage holds immutable source blobs, versioned objects, public observations and derived indexes. All three use one authenticated State Service; the UI does not maintain a competing authoritative database.

Every canonical object has an authority, object identity, type, revision, visibility and payload. Writes carry an operation identity and an expected revision. An existing operation receipt is reconciled instead of blindly replaying an action. Conflicting revisions do not silently overwrite one another. A changed dependency makes old evidence stale for new acceptance, while its historical record remains available.

Search indexes and UI counts are derived views. They can be rebuilt from permitted canonical objects and sources. Changing an index is not a substitute for recording a canonical decision. Hashes lock file, revision and environment identity; they do not establish semantic equivalence, factual truth or the contents of a model's private thought.

## Object responsibilities

A TaskContract states the objective, explicit constraints, authorized execution route and required work steps. A ResponseContract describes the result expected from a step. An Artifact identifies a source or produced result and its immutable blob. Evidence records an observation with its actual coverage. Validation records a registered verifier result for a specific property, Task revision and environment. It is not a model's statement that its own work succeeded.

SemanticCard, FailureCase and FailurePattern hold source-bound candidate explanations and conditions. Relations connect cases, principles and branches. Affiliation describes semantic belonging rather than a folder name. An adoption decision is separate from retrieval or candidate generation. A title, model label or search score cannot authorize adoption.

## Preparing and executing a task

Before execution, reconcile the live authority and schema, source and installed identities, actually loaded service, current Task and policy revisions, active leases, queues, uncertain receipts and costs. Historical success is evidence about its original environment; it is not automatically success for the current build. Another window's active lease must remain respected.

Prepare the exact current Task through the mapped host connection. The resulting capsule must be ready and include mandatory obligations. If required context exceeds its budget, split or revise the contract explicitly; do not truncate away the user's important requirement. Optional retrieval remains bounded and does not turn an entire historical corpus into round-by-round context.

User additions during execution steer the same task unless they clearly replace it. At a meaningful work node, check whether the preceding work actually satisfied the objective, whether a required step was missed and whether a correction should become a reusable candidate. Preserve public inputs, outputs, tool receipts and native locators. Do not fabricate sessions, end notifications or successful callbacks.

## Four distinct kinds of reusable asset

An information reference points to a source without endorsing it. Knowledge context proposes information or an explanation for the current task. A semantic principle describes applicability, exclusions and conditional branches. A registered executable constraint enforces a finite property at an implemented entry point.

The first three do not automatically become the fourth. A historical suggestion is not current permission. A candidate based on an unread attachment does not establish what the historical AI read. Domain truth, source fidelity, current-host judgment and independent verification have different evidence requirements.

## Semantic comparison

Compare actual triggers, expected behavior, observed behavior, applicable conditions, exclusions and corrections. Two different descriptions under equivalent conditions may link to a common principle. A shared principle with different conditions retains branches. Similar error wording can have different causes. A shared template can trigger independent problems. Insufficient evidence remains unresolved.

Mechanism families and lexical scores locate candidates; they do not merge them. Freeze a discrimination set before judging it. Include equivalent descriptions, conditional branches, different causes under similar wording, independent problems under a shared template and normal or insufficient-evidence boundaries. Record false merges, missed equivalences and corrections separately. Copying an existing record and finding it again is not this test.

## What the historical 900 contributed

Structural archival covered a frozen set of 2,531 conversations. Detailed extraction covered 900 sources and produced 3,793 knowledge candidates and 1,980 issue or boundary instances. Those are different achievements. The semantic review baseline comprises 151 pairs involving 115 instances; 1,865 instances have not received that review. Related and condition-extension labels are not confirmed merges.

The architectural contribution is a source-to-candidate-to-comparison-to-retrieval chain, explicit condition preservation, registered finite checks and a UI that exposes what a candidate means and where it came from. Some protections existed before the 900; required-step protection was also strengthened by later user corrections. It would be inaccurate to attribute every engineering change to the historical extraction or to describe every instance as an independent hard rule.

Five registered check families currently concern literal source quotations, delivery with current validation, declared protected baselines, uncertain receipt replay and explicit required work steps. They constrain registered UACF boundaries, not arbitrary host tools. They cannot guarantee that an unconnected ordinary chat will stop the model from writing an unsupported completion claim.

There is currently no universal rule that counts failed attempts and forces every host to reread the entire architecture after three failures. A future finite implementation would need an explicit definition of an attempt, the required structural sources, a controlled execution boundary and positive and negative acceptance cases. The existing protections require current dependencies and prevent unchecked registered delivery; they should not be described as that universal retry rule.

## Preparation, delivery, use and benefit

Task-specific retrieval first provides a principle and its applicability and exclusion conditions. Model version is a retrieval hint; genuinely general constraints can apply across models. Original source conditions are read only when needed. Public advisory context is limited to three modules and 4,000 bytes.

Preparation records the chosen set and bytes. Delivery needs a real host receipt. Demonstrated use needs an observable result or tool action corresponding to the lesson. Benefit needs task acceptance or a measured reduction in omissions or rework. These states must remain distinct. A retrieval hit is not evidence that the AI used it. A successful canary is not a normal model work session.

## Incremental capture and minimal-cost triggers

The trigger policy uses a bounded annotation of the current public work node: explicit capture request, confirmed correction, meaningful requirement change, progress, explicit satisfaction or completion, dissatisfaction, severity and short daily work. Emotion alone is not proof of error. Context volume alone is not a count of effective instructions.

Ordinary meaningful signals accumulate; three can prepare incremental capture. A fifteen-minute minimum interval coalesces ordinary captures. Explicit requests and critical corrections can prepare immediately. A preparation decision is not a capture receipt. The last actual captured source timestamp, rather than a request timestamp, controls subsequent accounting.

A periodic service sweep inspects opted-in local Task metadata without another model call. It rotates bounded pages so later Tasks are not starved. Seven-day inactivity or a day without inspection requires metadata checking. It does not imply access to every conversation in a cloud account and does not authorize paid full-history extraction.

Native hook delivery and public API back-reading are different transports. A persisted completed turn can supply real public observations and an observed completion through the official read-only API. It must be labelled as back-reading, not as proof that a live hook ran at the original moment. Current-host annotations interpret real source events; they do not invent end events. Automatic end capture and fillback must be accepted in the actual deployment before they are called verified.

## Private provenance and shareable modules

The private layer preserves real identities, revisions, original conditions and derivation basis. The public layer contains a bilingual abstract principle, applicability, exclusions, synthetic positive and negative examples, generic topics and limitations. Public bundles omit private conversation quotations, UUIDs, local paths, credentials and host bindings.

Existing settled candidates can be projected without repeating extraction. A changed public projection invalidates its review. A duplicate slug requires an explicit revision instead of silent merging. A local owner can open one exact linked source and its original conditions; that private response is not included in an export.

Importing a selected public bundle creates locally reviewable drafts and records its stated source and license basis. It does not invent personal historical provenance or install executable rules. Conflicting principles are rejected before importing the bundle's modules. Local review is required before a new imported module becomes eligible for advisory context. Mechanical privacy scans supplement, rather than replace, semantic review of the release scope.

## User operations

Unpack into a user-writable directory. Read the guide, then run Start-UACF or the Chinese launcher. The bootstrap locates a supported Python installation, installs pinned dependencies in an isolated environment, initializes an empty local authority when needed and opens the authenticated library. A missing-Python branch uses the official Windows installation mechanism; existence of that branch is not evidence that it was exercised on a fresh machine.

Choose a host configuration helper only for a host you have installed. Codex, Pi and DSH helpers preserve existing configuration and record their owned modifications. Configuration success is distinct from a running host actually loading the adapter. Do not replace a working service or port occupant without checking identity.

In the UI, create or resume a Task, inspect relevant knowledge and issues, read conditions, prepare context and follow the current required steps. Use the work update entry to record a meaningful result or correction. Create a sanitized draft from selected existing sources, review the exact projection and export only the public candidate. For received modules, import and review before use. Retain unresolved attachments and unverified domain claims.

## Budget and uncertain outcomes

External dispatch requires an authorized independent account, a known quotation and a conservative reservation. The latest authorization permits up to 100 new sources within a total of twenty CNY. It does not expand the historical batch4 limit or borrow another project's funds. Historical receipt ratios are estimates, not current price quotations.

Reserved, dispatched, response-known and unknown outcomes are reconciled before another action. Reuse known successful output. Unknown cost remains unknown rather than zero. A paid batch is not started to conceal a failed architecture acceptance check. Checkpoints at 10, 30, 60 and 100 verify source coverage, conditions, end observations, fillback, demonstrated use, UI counts, fees and preserved originals. Stop further additions on failure.

## Installation identity, removal and recovery

Generated means files exist. Installed means they are placed at a declared location. Loaded means a process reports the corresponding loaded identity. Called means a real invocation is observed. Verified binds a property to the frozen revision and evidence. Partial preserves a material missing part. These labels do not advance automatically together.

A clean installation must show zero historical sources and operate without DSH, DeepSeek, old accounts or machine-specific paths. A historical 900 cap is not a general acceptance limit. Dependency installation should be reproducible from locks and official sources; third-party wheels or code without redistribution permission are not bundled.

Removal reverses the installer's own modifications only when their current identities still match, and preserves user data and history. Backup recovery occurs in a new isolated root with a new authority, paused dispatch and explicit host remapping. It does not roll back the live database or replay paid actions.

## Public release and contribution

Build a clean whitelist export without the old .git directory. Exclude databases, raw archives, private assets, logs, evidence, credentials, dependencies, local configurations and withdrawn packages. Scan both the candidate package and any proposed public history. Each subsequent code change needs a new freeze and relevant verification.

Document actual dependencies and licenses, conceptual references and withdrawn approaches separately. MRS/MPH and other excluded old packages are not redistributed. Do not turn an early abandoned proposal into a claim that its code is present. Preserve the lawful remediation account. NOTICE, third-party records, the SBOM, exclusions and the upload manual accompany the candidate.

Contributions should use sanitized general principles, preserved conditions, synthetic tests and reproducible changes. They should not upload private originals in an attempt to improve coverage. More instances are not evidence of unlimited rule growth or complete factual acceptance. A final release still requires the project owner's license choice and a verified authorized publishing account.


## Latest observed continuation, 7 October 2026

Apache-2.0 was explicitly selected by the owner. The complete English design and both user guides are present. Three abstract advisory modules retain private provenance locally. The UI resolves original conditions and imports public modules as drafts; unreviewed export and context use are refused. A real cold start exposed inherited Windows pipe handles; the repaired launcher now returns successfully. A browser file-picker crash remains a host limitation; pasted public JSON was tested through the real UI instead. The missing authenticated mutation fields on the import button were found and repaired.

Official read-only public observations of a genuinely completed, explicitly mapped Codex turn reached the shared source/candidate/comparison/backfill chain without a new model turn or private reasoning capture. This is public back-reading, not verified live-hook delivery. The active turn has not completed yet. Metadata sweeps now rotate beyond the first sixty-four Tasks, without model calls.

One hundred unread sources were frozen separately from the earlier nine hundred, under an independent twenty-yuan authorization. Ten were extracted in the first production segment, but review, backfill and publication are incomplete. A checkpoint found that external extraction checked a context without delivering its advisory lessons. Later sources were paused and future request delivery was repaired; settled requests are retained rather than replayed. No claim of one hundred accepted sources is made. Read attachments, independent semantic truth and universal host enforcement remain distinct obligations.

The source suite passed 177 tests. The clean candidate installed and displayed actual zero counts. A later Windows temporary-service cleanup error was fixed and its four transport tests passed again; changed files need a fresh freeze and relevant checks. Firefox page capture failed, so account ownership/login has not been verified and nothing has been uploaded to GitHub.


## Historical verification addendum · 2026-10-07 14:00 UTC

The latest clean public candidate passed all 178 tests. Reviewed synthetic module import/export, a current-host-only ordinary task plan, and isolated backup/recovery passed. Uninstall checked data preservation; an absent deployment pointer is an idempotent no-op, not proof of restoring a native host configuration. Native host loading, live hooks and the current normal-work end remain partial. The populated live deployment validation is still in progress. Ten new historical sources were extracted, zero fully reviewed or published; further extraction is stopped at the failed architecture checkpoint. Twenty-three requests settled with a conservative peak-price usage bound of CNY 0.768499; the provider invoice remains unknown. This package is licensed Apache-2.0 and has not been uploaded.


## Final frozen scope · 2026-10-07T22:16:14.812604+00:00

This is the current scope; earlier dated addenda are historical records. Complete Chinese/English system descriptions, full user guides, phase-two operations, Supplement 04 and the dated migration account are included. Apache-2.0 covers the first-party clean public release; the private Git history is preserved locally and excluded.

The source and clean official-dependency installation both passed 187 tests. A real empty-store browser displayed zero sources, candidates and issues. Current-schema initialization creates no legacy batch3/batch4 spending authorization. Ordinary work uses the current host without DSH, DeepSeek or an old local ledger. Real deployment-pointer removal preserved the database hash; isolated restoration created another authority, passed integrity checks and replayed no external actions. Synthetic isolated host configuration was parsed by native Codex and restored with drift checks; this is not universal native-host verification.

This explicitly mapped real chat exercised public observation, an actual previous normal end, in-work source capture, candidates, comparison and same-queue return. Incremental capture retained 68 new public records after the previous source boundary without repeating the original request. Detection and current-host return created no extra GPT turn. A known stored observation was reconciled without replaying the original work. Small structured signals and a rotating metadata sweep bound detection cost. A public read-back transport is not a verified live hook; arbitrary hosts, account-wide access and this still-future final end are not preclaimed.

All 100 new sources, disjoint from the old 900, contributed 2,417,919 public characters to canonical candidate publication. The current host read 21 complete selected sources (9.9936% of text). Evidence survives at 10/30/60/100 checkpoints. The old 900 were not re-extracted. Structural coverage, detailed candidate coverage, semantic review and domain truth remain distinct. The old 1,980 issue/boundary instances have not all received semantic duplicate review. Conditions, separate branches, independent issues and insufficient evidence survive; retrieval scores and mechanism families cannot approve merges.

Guidance reached later paid requests with actual prompt receipts. Host review excluded unsupported language failures and checked cross-function output and timing contracts. Model declarations alone did not establish use. The first-ten delivery gap and original settled format failures were retained; formatting repairs reused known output. No new hard rules were generated. Five existing finite registered guards control only admitted execution/delivery boundaries, not private reasoning or arbitrary tools. Three reviewed shareable advisory principles contain abstract conditions and synthetic examples, while private provenance links remain local. The observed conservative peak-price usage bound is CNY 4.406337 within the separately authorized CNY20 budget; the provider invoice is unknown.
