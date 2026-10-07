# UACF — 持续AI工作的任务与经验系统

UACF helps research, writing, media and engineering work preserve requirements, sources, corrections and conditional lessons across AI sessions. 普通用户可通过本地前台使用，不必先学习Git命令。

先读[中文使用手册](docs/baseline/UACF_普通用户使用手册_中文.html)，解压后运行根目录的“开始使用UACF.cmd”。Read the [English user guide](docs/baseline/UACF_User_Guide_English.html), then run Start-UACF.cmd. Host configuration helpers are optional and preserve existing settings. Configuration is separate from actual native loading.

完整设计：[中文总说明](docs/baseline/UACF_正式完整版设计总说明.html) / [Complete English design](docs/baseline/UACF_Complete_System_Design_English.html). [900之后到底改变了什么](docs/baseline/UACF_900之后架构到底改变了什么.html) describes concrete capabilities and remaining boundaries in ordinary language.

Shareable advisory modules are in modules/lessons.json. Import them through the UI as reviewable drafts, check applicability and license, and review locally before context use. Private source links and originals are absent. Importing guidance does not install executable rules.

The project uses Apache-2.0. Dependencies and hosts are installed from official channels; their code and wheels are not bundled. See NOTICE.md, THIRD_PARTY.md, SBOM.json and LICENSE-GAPS.md. Private chat data, databases, logs, credentials, old Git history and excluded MRS/MPH packages are not distributed.

Capability limits: full900 semantic review is incomplete; account-wide cloud monitoring, arbitrary host-tool enforcement and private-reasoning validation are not provided. Public API back-reading is distinct from live hook delivery. Missing-Python execution and actual loading in every native host remain separately testable. Counts and evidence do not imply domain truth.

For contribution and publication use CONTRIBUTING.md, SECURITY.md and UPLOAD-GUIDE.md. Share abstract conditions and synthetic examples; do not upload personal originals.
