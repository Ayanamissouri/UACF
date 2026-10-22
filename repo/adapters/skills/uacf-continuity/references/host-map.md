# One Task, different native entry points

| Host | Read current state | Native preparation and limitations |
|---|---|---|
| Codex | Installed UACF MCP context, work brief and capability tools when actually listed | Managed hook discovery is not proof this desktop session invoked every hook; public polling captures evidence but cannot block a prior tool call. |
| Pi | `/uacf-prepare`, UACF context tool; `/uacf-brief` when present | Existing extension prepares at input/before-agent-start and checks tool calls. A new extension version needs actual loading evidence; do not assume another session reloaded. |
| DSH | Installed UACF context/brief tools | Native prompt assembly and pre-execution guard belong to the installed plugin. Claude-style Skill frontmatter hooks are not DSH lifecycle listeners. |

Read capability observations by machine, host version, profile, source identity and native session. Generated, installed, loaded, called and verified are independent observations. Missing proof is unobserved, not proof a tool is unavailable; discovery and actual calls provide separate evidence.

Use the tools actually exposed here. If a specialist code tool is missing, use existing file search and source inspection with an explicit coverage difference. If no delegated agent is available, work sequentially. Shared services with mutable project state need project/session isolation. Unknown external results must be reconciled under the original operation identity, never resubmitted through another Host.

Do not install planning-with-files global process gates into a multi-session DSH process: process-level PLAN_ID/PWF_PLAN_ROOT cannot safely select concurrent Tasks. UACF-derived per-Task views and existing preparation remain the current integration.
