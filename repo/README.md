<a id="chinese"></a>

# UACF — 让AI工作保留要求、来源和经验

**English version follows below — [Jump to English](#english).**

UACF（Unified Agentic Continuity Fabric，统一智能体连续性织体）是一套用于管理历史数据资产、对话日志和长期项目状态，并帮助AI更有效利用既有上下文与经验的本地连续性基础设施。

它最初来自三个非常直接、彼此独立的需求：

1. 整理和利用长期积累的历史对话、资料、任务记录和其他数据资产；
2. 让AI更准确地理解要求、复用已有经验、减少重复犯错；
3. 提供一个能够查看、管理和控制这些资产与任务关系的项目交互前端。

最初，这三个需求分别形成了彼此独立的架构。但在后续测试与开发中，我们逐渐发现，它们实际上高度耦合，并且会持续相互影响：有效的数据资产管理才能为AI提供优质、可追溯的控制条件；良好的执行约束才能带来稳定、丝滑的前台交互；准确的指令输入与识别才能保证工作不跑偏；完善的读写系统才能真正利用已有数据资产，并在新的工作中继续补充和修正它们。

因此，UACF最终不再只是一个聊天记录整理工具、一个控制层或一个项目管理前端，而逐步发展为一套面向长期AI工作的连续性系统。它关注的不只是“保存聊天记录”，而是让一个项目能够跨会话、跨模型、跨Harness和跨执行环境持续存在，并保留任务、要求、来源、证据、决策、失败、纠正、验证和其他能够影响后续工作的状态。

换句话说，UACF试图解决的是：

> 当一个长期项目已经进行了几十次甚至数百次AI对话之后，新的AI应该怎样知道过去做过什么、为什么这么做、哪些地方已经失败过、哪些要求仍然有效，以及当前任务真正需要取回哪些历史信息。

UACF不要求把全部历史内容重新塞入每一次上下文，而是尽可能从长期资产中选择与当前任务有关的内容，并把新的任务结果、纠正、验证和适用条件重新沉淀到同一套连续性系统中。

UACF可以用于科研、软件、工程项目、办公等长期AI辅助工作，也可以辅助自然科学与社会科学模型、金融量化模型、文件整理、分析与写作等不同类型的任务。它并不限定具体领域，而是为需要长期积累资料、持续调用AI、反复修正工作方法和保留项目状态的工作提供统一的连续性基础。

## 1. UACF主要解决什么

长期使用AI时，问题通常并不是“没有历史记录”，而是历史记录太多、太散，并且缺少能够被后续任务直接利用的结构。

一个长期项目可能同时存在：

- 几十到几百个历史对话；
- 大量文件、网页、笔记和研究资料；
- 曾经确认过但后来容易被遗忘的要求；
- 已经验证过的解决方法；
- 失败过的尝试和对应原因；
- 只在特定条件下成立的经验；
- 被新版本取代的旧结论；
- 不同AI、不同Harness和不同执行环境产生的工作结果。

普通聊天记录能够保存其中很多内容，却不能保证新的AI在正确的时间读取正确的部分。

UACF因此把“保存历史”与“使用历史”分开处理：历史数据可以长期保存，而当前AI只获得当前任务需要的上下文、经验、证据和约束。

## 2. 为什么这会让AI工作得更好

UACF不修改模型本身，也不承诺AI永远不会犯错。

它主要通过改善AI能够获得的信息和任务状态，降低长期工作中反复出现的一些失败模式，例如：

- 忘记过去已经确认的要求；
- 在长上下文中让重要指令逐渐失去权重；
- 重复尝试已经失败过的方法；
- 忽略结论的适用条件；
- 无法区分当前有效状态和历史状态；
- 重新阅读大量无关历史内容；
- 错误继承已经被纠正或废弃的结论；
- 在跨会话、跨模型或跨执行环境工作时丢失项目连续性。

对于自然语言本身的误读，例如对夸张、转折、否定、条件关系、修辞或表达习惯的理解错误，UACF不能从根本上消除模型能力限制。但它可以保存明确的纠正、例外、失败记录和长期要求，让后续任务能够继续利用这些经验，而不是每次从零开始。

## 3. UACF保存的不是单纯“记忆”

UACF的目标不是建立一个无限增长的聊天记忆库。

它更关心不同信息在项目中的作用，例如：

- Project：长期项目；
- Task：当前或历史任务；
- Evidence：资料与证据；
- Decision：已经形成的决策；
- Failure：失败、误判和踩坑记录；
- Validation：实际验证结果；
- Provenance：来源与形成过程；
- Asset：文件、对话、资料和其他数据资产。

这些对象可以继续形成关系，使系统知道一项结论来自什么证据、替代了什么旧结论、在哪次执行中失败、经过了什么验证，以及以后在什么条件下应该重新取回。

因此，Conversation不等于Project State。聊天只是工作发生的一个界面，而长期项目状态需要独立保存。

## 4. 从哪里开始

如果你只是希望先使用UACF，而不是研究它的架构，可以直接从Release包开始。

1. 到本仓库的 [Releases](https://github.com/Ayanamissouri/UACF/releases) 下载完整ZIP，解压到你希望长期保存资料的文件夹。
2. 双击 [开始使用UACF.cmd](../开始使用UACF.cmd)。首次安装使用官方Python依赖；随后打开本机前台。
3. 先阅读[中文用户手册](docs/baseline/UACF_普通用户使用手册_中文.md)。普通任务默认使用当前AI宿主，需要额外预算的外部模型属于可选路线，并需要显式授权。
4. Codex、Pi、DSH用户可使用对应的配置入口：[Install-for-Codex.cmd](../Install-for-Codex.cmd)、[Install-for-Pi.cmd](../Install-for-Pi.cmd)、[Install-for-DSH.cmd](../Install-for-DSH.cmd)。

也可以先双击包内 [阅读说明.html](../阅读说明.html) / [Read-UACF.html](../Read-UACF.html)，或打开[完整阅读导航](docs/baseline/UACF_阅读导航.md)与[逐项交付核对](docs/baseline/UACF_交付要求逐项核对.md)。

需要特别注意：安装配置、宿主加载和实际调用是三个不同状态，不能用安装成功代替实际调用验收。

## 5. 历史数据与本地资产

UACF默认面向本地长期资产管理。

私人原件、数据库、宿主令牌、真实来源链接以及未经审查的个人对话，应当继续保留在本地环境中。

不要把下载目录里的代码本身当成你的资料备份。

如果需要分享经验，推荐只导出经过复核的抽象原则、适用条件、排除条件和合成示例，而不是直接公开私人历史数据。

UACF不会因为某段历史资料被系统使用，就自动把它变成公开内容。

## 6. 条件化经验，而不是死规则

UACF中积累的经验不应被理解为“以后永远执行这一条规则”。

一项经验可能只在特定模型、版本、项目、数据、任务或者环境下成立。

因此，系统更强调：

**经验 + 条件 + 反例 + 来源 + 验证范围**

而不是：

**经验 = 永久规则**

这也是UACF使用Failure、Validation、Provenance和条件化经验，而不是简单维护一张“AI应该怎么做”的静态规则表的原因。

## 7. 跨模型与跨执行环境

UACF不绑定某一个AI模型，也不要求某一种固定Harness。

同一个项目可以在不同阶段使用不同执行端，例如：

- ChatGPT；
- Codex；
- Pi；
- DSH；
- 本地模型；
- 其他未来接入的Agent或执行环境。

执行端可以变化，但项目的历史资产、状态、证据、纠正和验证不应因此全部重新开始。

UACF试图提供的正是这一层连续性。

上述列表包括工作来源与接入方向，不表示每一种执行端都已完成现场集成验收；当前适配与实测范围见[验证说明](docs/public/VERIFICATION.md)。

## 8. 当前系统边界

UACF是连续性基础设施，而不是一个能够自动保证结果正确的万能Agent。

它不能替代：

- 模型自身的推理能力；
- 对事实和来源的人工判断；
- 软件测试；
- 科学实验；
- 安全审查；
- 专业领域验证。

它能够做的是让这些验证、失败和纠正不再只存在于某一次孤立对话中，而可以成为后续工作的可复用资产。

所有“已经验证”的声明，也只适用于对应版本、环境和实际测试范围。

## 9. 读懂这套系统

- [正式完整中文设计总说明](docs/baseline/UACF_正式完整版设计总说明.md)
- [第二阶段运行与操作模式](docs/baseline/UACF_第二阶段整体运行与操作模式.md)
- [补充04：原计划到当前实现的变化](docs/baseline/DSH_第一阶段设计补充04.md)
- [900个来源之后，架构到底改变了什么](docs/baseline/UACF_900之后架构到底改变了什么.md)
- [从早期工作台到当前流程的完整迭代史](docs/baseline/UACF_从早期工作台到当前流程的迭代说明.md)
- [七项问题修正与实际验收](docs/baseline/UACF_七项问题修正与验收说明.md)
- [验证范围与限制](docs/public/VERIFICATION.md)
- [参考、许可与排除范围](REFERENCES.md) · [第三方说明](THIRD_PARTY.md)
- [完整英文设计](docs/baseline/UACF_Complete_System_Design_English.md) · [英文用户手册](docs/baseline/UACF_User_Guide_English.md)

本次文档修订将过时现场状态移入历史附录，当前有效说明放在前面。

更多可点选的源码、共享模块、许可和贡献入口见文末[文件与代码导航](#files-and-code)。

---

<a id="english"></a>

## English

**中文版在前面 / Chinese version above — [返回中文版 / Back to Chinese](#chinese).**

### UACF — Preserve Requirements, Sources and Experience Across AI Work

UACF, the Unified Agentic Continuity Fabric, is a local continuity infrastructure for managing historical data assets, conversation logs and long-running project state, while helping AI systems make better use of existing context and accumulated experience.

It began with three practical but initially separate goals:

1. organize and reuse historical conversations, files, task records and other long-term data assets;
2. help AI systems interpret requirements more accurately, reuse prior experience and avoid repeating known failures;
3. provide a clear project-facing interface for inspecting and managing these assets and their relationships.

These goals were originally implemented as three largely independent architectures. During later testing and development, however, it became clear that they were tightly coupled and continuously influenced one another. Effective asset management is necessary to provide reliable and traceable control conditions for AI systems; good execution constraints are necessary for stable and smooth frontend interaction; accurate instruction input and recognition are necessary to keep work aligned with user intent; and a complete read/write system is necessary both to make full use of existing assets and to improve them through new work.

UACF therefore developed beyond a conversation archive, a control layer or a project-management frontend. It became a continuity system for long-running AI-assisted work.

Its central concern is not simply how to preserve chat history, but how a project can remain coherent across conversations, models, Harnesses and execution environments while retaining tasks, requirements, sources, evidence, decisions, failures, corrections, validations and other state that may matter later.

In practical terms, UACF addresses a common problem:

> After dozens or hundreds of AI conversations, how should a new AI instance know what has already been done, why earlier decisions were made, what has failed before, which requirements still apply, and which parts of the historical record are actually relevant to the current task?

UACF does not attempt to place the entire project history into every prompt. Instead, it aims to retrieve the subset of prior context, evidence, constraints and experience that is relevant to the current task, while feeding new results, corrections, validations and applicability conditions back into the same continuity system.

UACF can be used in research, software development, engineering projects, office work and other long-running AI-assisted workflows. It can also support natural-science and social-science modeling, quantitative finance models, file organization, analysis and writing. It is not tied to a particular domain; its purpose is to provide continuity wherever work depends on accumulated material, repeated AI use, iterative correction and persistent project state.

### 1. What UACF addresses

Long-term AI work usually does not suffer from a complete absence of history. The problem is that the history becomes large, fragmented and difficult to reuse correctly.

A project may contain:

- dozens or hundreds of historical conversations;
- large collections of files, webpages, notes and research material;
- requirements that were previously confirmed but later forgotten;
- solutions that have already been validated;
- failed approaches and the reasons they failed;
- lessons that are valid only under specific conditions;
- conclusions superseded by newer versions;
- work produced by different AI systems, Harnesses and execution environments.

Ordinary conversation history can preserve much of this information, but it does not guarantee that a future AI system will retrieve the correct information at the correct time.

UACF therefore separates storing history from using history. Historical assets can remain persistent, while the current AI receives only the context, evidence, constraints and prior experience needed for the current task.

### 2. How this helps AI work more reliably

UACF does not modify the underlying model and does not guarantee that an AI system will never make mistakes.

Instead, it improves the information and project state available to the AI, reducing recurring failure modes such as:

- forgetting previously established requirements;
- allowing important instructions to become diluted in long contexts;
- repeating approaches that have already failed;
- ignoring applicability conditions;
- confusing current state with historical state;
- rereading large amounts of irrelevant material;
- carrying forward conclusions that have already been corrected or superseded;
- losing project continuity across conversations, models or execution environments.

Natural-language misunderstandings, including mistakes involving exaggeration, contrast, negation, conditional logic, rhetoric or writing conventions, cannot be eliminated purely by continuity infrastructure. However, explicit corrections, exceptions, failure records and persistent requirements can be retained and surfaced later, allowing future work to benefit from prior experience instead of starting from zero.

### 3. More than a memory store

UACF is not intended to become an indefinitely growing memory dump.

It distinguishes between different kinds of project information, including:

- Project;
- Task;
- Evidence;
- Decision;
- Failure;
- Validation;
- Provenance;
- Asset.

These objects can be connected so that the system can retain why a conclusion exists, which evidence supports it, what it superseded, where an approach failed, how a result was validated and under what conditions it may be useful again.

For this reason, Conversation is not equivalent to Project State. Conversations are working surfaces; durable project continuity must exist independently of any single conversation.

### 4. Getting started

If you want to use UACF rather than study its internal architecture, begin with the Release package.

1. Download the complete ZIP from [Releases](https://github.com/Ayanamissouri/UACF/releases) and extract it into a folder intended for persistent UACF data.
2. Run [Start-UACF.cmd](../Start-UACF.cmd). The first setup uses the official Python dependencies and then opens the local frontend.
3. Read the [English user guide](docs/baseline/UACF_User_Guide_English.md), or the [Chinese user guide](docs/baseline/UACF_普通用户使用手册_中文.md). Normal tasks use the current AI host by default; external models that require additional budget are optional and require explicit authorization.
4. Codex, Pi and DSH users can use the corresponding configuration entry points: [Install-for-Codex.cmd](../Install-for-Codex.cmd), [Install-for-Pi.cmd](../Install-for-Pi.cmd), and [Install-for-DSH.cmd](../Install-for-DSH.cmd).

You can also begin with [阅读说明.html](../阅读说明.html) / [Read-UACF.html](../Read-UACF.html), or open the [complete reading navigation](docs/baseline/UACF_阅读导航.md) and [delivery checklist](docs/baseline/UACF_交付要求逐项核对.md).

Installation, successful host loading and verified use by an AI during a real task are three different states. A successful installation must not be treated as proof of actual runtime integration.

### 5. Historical data and local assets

UACF is designed around persistent local asset management.

Private originals, databases, host tokens, real provenance links and unreviewed personal conversations should remain in the local environment.

Do not treat the downloaded program directory itself as a backup of your project data.

When sharing experience, prefer reviewed abstract guidance, applicability conditions, exclusion conditions and synthetic examples rather than exposing private historical material.

Using historical information inside UACF does not automatically make that information public.

### 6. Conditional experience, not permanent rules

Experience stored by UACF should not be interpreted as a permanent instruction that must always be followed.

A lesson may only be valid for a particular model, release, project, dataset, task or execution environment.

UACF therefore emphasizes:

**experience + conditions + counterexamples + provenance + validation scope**

rather than:

**experience = permanent rule**

This is why Failure, Validation, Provenance and conditional lessons are more important than a static rulebook describing how an AI should always behave.

### 7. Cross-model and cross-environment continuity

UACF is not bound to one model or one Harness.

A single project may use different execution environments at different stages, including:

- ChatGPT;
- Codex;
- Pi;
- DSH;
- local models;
- other future Agent systems.

Execution environments may change, but project assets, state, evidence, corrections and validation history should not need to restart from zero.

That continuity layer is the role UACF is intended to provide.

This list includes work sources and integration targets, not a claim that every environment has passed live integration tests. See the [validation scope](docs/public/VERIFICATION.md) for currently observed adapter capabilities.

### 8. System boundaries

UACF is continuity infrastructure, not a universal Agent that automatically guarantees correct results.

It does not replace:

- model reasoning;
- human judgment of facts and sources;
- software testing;
- scientific experiments;
- security review;
- domain-specific validation.

Its role is to make those validations, failures and corrections reusable parts of long-term project state instead of leaving them trapped inside isolated conversations.

Any verified claim applies only to the documented release, environment and actual test scope.

### 9. Further documentation

- [Complete English design specification](docs/baseline/UACF_Complete_System_Design_English.md)
- [English user guide](docs/baseline/UACF_User_Guide_English.md)
- [Complete Chinese design specification](docs/baseline/UACF_正式完整版设计总说明.md)
- [Phase 2 runtime and operation model](docs/baseline/UACF_第二阶段整体运行与操作模式.md)
- [Supplement 04: changes from the original plan to the current implementation](docs/baseline/DSH_第一阶段设计补充04.md)
- [How the architecture changed after reviewing 900 sources](docs/baseline/UACF_900之后架构到底改变了什么.md)
- [Full chronology from the early workbench to the current workflow](docs/baseline/UACF_从早期工作台到当前流程的迭代说明.md)
- [Seven corrections and actual acceptance scope](docs/baseline/UACF_七项问题修正与验收说明.md)
- [Validation scope and limitations](docs/public/VERIFICATION.md)
- [References, licensing and exclusion scope](REFERENCES.md) · [Third-party notices](THIRD_PARTY.md)

Outdated operational state has been moved into historical appendices so that current guidance appears first.

Licensed under [Apache-2.0](../LICENSE). The public repository was exported with a clean initial history and excludes the private project's Git history and personal assets; subsequent public revisions preserve that clean history. Contributions should document applicability conditions, counterexamples, permission to share and evidence for the scope actually tested. See [CONTRIBUTING](CONTRIBUTING.md) and [SECURITY](SECURITY.md).

---

<a id="files-and-code"></a>

## 文件与代码导航 / Files and code

|入口 / Entry|文件或目录 / File or directory|
|---|---|
|核心源码 / Core source|[repo/uacf](uacf)|
|前台 / Local frontend|[control-surface](apps/control-surface)|
|宿主适配器 / Host adapters|[adapters](adapters)|
|合同与测试 / Contracts and tests|[contracts](contracts) · [tests](tests)|
|运行与安装工具 / Operation and installation tools|[ops](ops)|
|源码说明 / Source-level README|[repo/README.md](README.md)|
|可分享经验模块 / Shareable advisory modules|[lessons.json](modules/lessons.json)|
|版本变更 / Change history|[CHANGELOG](CHANGELOG.md)|
|许可与来源 / License and provenance|[LICENSE](../LICENSE) · [NOTICE](../NOTICE.md) · [source NOTICE](NOTICE.md) · [REFERENCES](REFERENCES.md)|
|第三方与依赖 / Third parties and dependencies|[THIRD_PARTY](THIRD_PARTY.md) · [SBOM](SBOM.json) · [locked requirements](requirements.lock)|
|许可缺口与排除范围 / License gaps and exclusions|[LICENSE-GAPS](LICENSE-GAPS.md) · [EXCLUSIONS](EXCLUSIONS.json)|
|贡献、安全与上传 / Contributions, security and upload|[CONTRIBUTING](CONTRIBUTING.md) · [SECURITY](SECURITY.md) · [UPLOAD-GUIDE](UPLOAD-GUIDE.md)|
|公开文件清单 / Public file manifest|[PUBLIC-MANIFEST](PUBLIC-MANIFEST.json)|

原有网页阅读版本也保留：[中文手册](docs/baseline/UACF_普通用户使用手册_中文.html) · [English guide](docs/baseline/UACF_User_Guide_English.html) · [中文总说明](docs/baseline/UACF_正式完整版设计总说明.html) · [English design](docs/baseline/UACF_Complete_System_Design_English.html) · [900之后的架构说明](docs/baseline/UACF_900之后架构到底改变了什么.html) · [七项修正说明](docs/baseline/UACF_七项问题修正与验收说明.html) · [网页阅读导航](docs/baseline/UACF_阅读导航.html)。

经验模块在前台中作为可审查草稿导入；先检查适用条件、排除条件与分享许可，再决定是否用于本地任务。导入经验不会安装可执行规则。

Advisory modules are imported through the UI as reviewable drafts. Check applicability, exclusions and permission to share before local task use. Importing guidance does not install executable rules.
