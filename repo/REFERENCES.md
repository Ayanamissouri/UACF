# References / 参考与最终采用边界

本表记录2026-10-04的定点接口研究，不表示整包安装、复制实现或第三方对本项目背书。作者以仓库公开维护组织/账号署名，不臆测自然人。固定修订只用于解释当时查看的版本。
This table records interface research on 2026-10-04. It does not claim copied implementations, bundled packages, deployment, endorsement or redistribution permission. Repository owners identify the credited maintainers.

|公开维护者 / Maintainer|研究入口 / Research source|当时修订 / Observed revision|本包边界 / Package boundary|
|---|---|---|---|
|modelcontextprotocol|[modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)|`5abed86c5317b833dd59907492d56c65981642aa`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|
|github|[github/github-mcp-server](https://github.com/github/github-mcp-server)|`71ef8266e48110974b13aef50b4df6ff9914ff68`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|
|microsoft|[microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)|`f183dad4a52965583e3cc1d59b88cdc279e2e57d`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|
|upstash|[upstash/context7](https://github.com/upstash/context7)|`bfa02ea67b5707fe0e0a673faa49d0f50b28c80b`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|
|oraios|[oraios/serena](https://github.com/oraios/serena)|`08d53bc9bf333a4ded2c472fb6cb581edb501b81`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|
|mem0ai|[mem0ai/mem0](https://github.com/mem0ai/mem0)|`abb81c88e1f738a8117d8293530fbc31a5ef8fd9`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|
|getzep|[getzep/graphiti](https://github.com/getzep/graphiti)|`b7fc30f2a1e288266760640164a37bdb7d1d0f28`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|
|obra|[obra/superpowers](https://github.com/obra/superpowers)|`8ca22dba9a94f28898bbce59f2537ff4d87c747d`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|
|agentsmd|[agentsmd/agents.md](https://github.com/agentsmd/agents.md)|`d001185d792eb6402a58e4cbef1c228b309ec25d`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|
|agentskills|[agentskills/agentskills](https://github.com/agentskills/agentskills)|`69ef37e9424c0a7ea9dd2293b559e43ec8176379`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|
|earendil-works|[earendil-works/pi](https://github.com/earendil-works/pi)|`f5d20047b3ad43d068a8eb61bd4e1f193bedbce6`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|
|openai|[openai/skills](https://github.com/openai/skills)|`49f948faa9258a0c61caceaf225e179651397431`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|
|steipete|[steipete/mcporter](https://github.com/openclaw/mcporter)|`9d3cf4f4a3b07eb625e1ad4d7196182dc24e0392`|接口与生态比较；未捆绑该仓库代码 / interface comparison; no repository code bundled|

Pi is an optional native host; its extension uses the host SDK and locked installation dependencies. MCP is the shared tool protocol. The first-party adapters are included; external host binaries and third-party wheels are installed separately from official sources. See THIRD_PARTY.md and SBOM.json for actual dependency declarations.

MRS/MPH及其他旧非开源包曾进入早期评估，但最终停止采用并排除；历史整改说明保留，排除代码、轮子、权重不重新分发。不能把早期设想写成最终采用。Wing Agent/Strata名称仅保留为早期研究线索；没有经过核实的作者与公开出处，故不虚构署名或许可，也不列为当前依赖。
MRS/MPH and other excluded legacy packages were discontinued after initial evaluation. No excluded implementation is redistributed. Early Wing Agent/Strata references are research leads with unconfirmed attribution, not current dependencies.

Apache-2.0 applies to the first-party public release. It does not relicense third-party material. Unresolved licenses remain gaps and their material is excluded.


## Durable instruction continuity research,2026-10-08

Reviewed primary project documentation for [Beads](https://github.com/gastownhall/beads) (persistent dependent tasks), [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) (checkpoint/resume), and [ContextSpindle](https://github.com/reacherwu/ContextSpindle) (authoritative task ledger separated from optional memory). These informed the separation of current instruction state and optional retrieval. UACF implements its scoped command lane inside its existing authenticated canonical State Service. No code, package or performance claim from these projects is redistributed or adopted as verification here. Future integration needs an exact version and its own permission review.

Current Codex context settings were checked against [official configuration documentation](https://learn.chatgpt.com/docs/config-file/config-reference). A model's catalog window, effective runtime window and resolved auto-compaction threshold are distinct. Local public metadata is an observation, not a promise of universal settings.
