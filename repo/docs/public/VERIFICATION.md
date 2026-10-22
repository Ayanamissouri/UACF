# Current verification — 2026-10-21

| Check | Observed scope |
|---|---|
| Development source | 229 tests passed |
| Reviewed public candidate | 229 tests passed |
| Isolated install from the official hash-locked requirements | Installed successfully; fresh authority; integrity and foreign-key checks passed |
| Isolated installed source | 229 tests passed |
| Isolated backup/recovery | Passed; no live store overwritten |
| JS/MJS syntax | All selected files passed Node syntax checks, without executing third-party model calls |
| Publication | Exact file/hash manifest, bounded privacy scan, ZIP file identity; remote proof recorded only after upload/download |

Revision .1 fixes the CI invocation to enable UTF-8 and explicitly skips the native Windows Codex test when that optional CLI is absent. The first CI failure remains visible in GitHub history; it is not a passing new-machine result. Local source/candidate/clean runs include the installed native CLI. Cloud CI result is reported independently.

The source/candidate/clean runs are separate executions of the same finite 229-test suite. They are not 687 independent requirements and do not prove arbitrary host or remote-device behavior. Tests cover current state/contracts, transport, source permissions, queues, revisions, workflow/metric evidence and configured boundaries. Old counts in historical guides remain historical.

The complete package excludes user data, native histories, credentials, machine configuration, private experiment scripts, old private Git history, vendor wheels, node_modules and old Pi runtime locks. Existing first-party Apache-2.0 licensing and dependency notices remain. No new paid model requests were made for this release work.

## Known limits

Native observer cross-workspace admission, generic default-Task verification registration and stale active-stage continuation are not repaired by this publication. Metric evidence code and its stage hook are present in this source package; existing running installations need controlled adoption. New-machine Python bootstrap without Python, every real host callback, cloud account-wide archives, semantic/domain truth and remote models/GPU performance remain separately verified. No production instance or remote computer was upgraded by publishing this release.


## 2026-10-22 organizing-upgrade regression

The complete public candidate passed **255 tests**. The organizing-upgrade subset passed **71 focused tests** across requirement admission/delivery, stage workflow, Host work, learning retrieval, archive-preservation guards, work verification and transport. The native Pi timeout contract verifies reconciliation through the exact original operation and no action resend. These are finite mechanical checks; they do not grade semantic understanding, domain truth, arbitrary Host callbacks or universal enforcement.

The local registered preservation verifier checked the pre-existing immutable archive revisions and project-file scope before packaging. Its private machine receipts, local paths and source locators are excluded. The public package contains no user archive, database, raw chat, local runtime log, credentials, `.git`, `node_modules`, virtual environment, vendor wheel or third-party runtime binary. Publication does not deploy this source to an existing installation.
