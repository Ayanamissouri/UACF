# 从早期DSH工作台到UACF：完整项目演变

截至2026年10月8日。本说明回答“项目最开始做什么，怎样一步步成为现在的架构”。按日期与工程阶段写实际内容，日期不是把聊天运行日志逐条抄过来。

## 如何核对这段历史

本次重新查看两处早期资料目录：原设置工作台与DSH架构搭建临时目录，登记46个顶层条目，检查19个工程ZIP、定点读取248个说明/合同/实现文件；相同包在两个位置的副本不算两次开发。另查当前私有Git的首批提交、阶段合同与E7/学习交接。没有运行旧安装器、回滚旧库或重新读取全部900正文。旧源代码、私人日志、API文件与原包不随此说明公开。

证据有三种时间：包/README自述日期、ZIP成员及文件系统创建/修改日期、实际提交/执行回执日期。复制和解压会改变文件系统时间，README也可能沿用旧版标题；遇到不一致时分别记录，不把mtime当独立的开发证明。本文使用日或阶段，不把10月7日每次脚本的秒数当项目历史。

## 9月15—16日：先让科研工作台可安装、可启动

早期安装日志与制作初始化文案先讨论DSH启动和科研/量化工作入口。9月16日Starter包把准备环境、固定DSH版本、启动网页、维护与恢复步骤组成可交付工具。PS5.1版本修补Windows脚本兼容性：避免使用与HOME/PROFILE冲突的变量，脚本编码与生成JSON/YAML编码区分。v2、v3继续修复启动与本地canary，而不是重新定义整个项目。

原意是让研究者少做环境折腾，能够在工作目录中留下计划、结果与证据。此时重点仍是“DSH工作台”，还不是跨所有宿主的统一权威库。包存在、安装步骤写完与真正启动成功分别记录。

## 9月17日：v4、v5及v5.1补齐底层能力

v4在v3上追加三项：原生Codex CLI/账号连接与DSH委托入口；合成隐私/外发检查；可执行插件供应链审计。主要链是DSH网页→主Agent→明确委托时的Codex子任务。原生账号由Codex持有，子任务是新的有界线程，不承诺继承任意ChatGPT网页对话。

v5 Foundation Followup和v5.1 PS51 Hotfix继续处理基础安装/审计流程及Windows兼容性。其README_FIRST仍沿用v4标题，因此不能只读标题推断它们完全相同；应结合新增脚本与版本说明核对。当前找到的是v5、v5.1和随后v6，尚未发现独立标名v5.4的包，不能凭记忆编造这一版本的实现。

## 9月18日：v6恢复链与v7—v7.4治理

v6从v5.1继续，为剩余DSH→Codex现场E2E失败增加R00—R08恢复链。它明确要求保留已有安装/认证，不重复登录、不修改系统代理注册表、不反复重试同一子任务失败。

v7把反复实验、失败、工具数量、修改次数、时间预算、受保护路径和修改前checkpoint组成治理插件。NORMAL默认同实验/同失败上限3；DEBUG/QUANT/SENSITIVE更紧，科研模式要求修改前新checkpoint。插件实际在DSH工具入口判断是否允许；停止后有有限审查通道，并要求总结证据和新的回合。它没有证明任意Codex工具都受控，也没有验证模型读懂了结构。

v7.1修正PS5.1安装审计误报；v7.2修补治理脚本；v7.3改用真实root调用身份，修复重复拦截canary；v7.4修复实验fingerprint：shell命令、workdir、background与sandbox保留，description/justification/timeout不影响身份。旧说明称其semantic identity，但这里的hash只识别声明的同一实验，不能当自然语言语义理解。

因此“以前没有重复失败/实验拦截”是错误的项目历史结论。正确说法是：旧DSH治理包已有这些有限拦截；它是否已加载、接到了当前UACF/Codex，需要新回执。旧包的“停止并审查”也不等同于任意宿主已强制重新阅读全结构。

同时形成GPT_ARCHIVE、V74A/V74B/V75等本地资产包，开始把来源、目录、候选与私人素材保存起来。候选包和个人档案不等于已审核的可公开资产。

## 9月19日：v8编排与v9控制面

v8把多AI角色、名册、分类方案、路由、并发、协议与薄宿主插件整合为编排层。包自述含70项编排测试，并提供dry-run安装步骤；这些自述是当时包内记录，不替代当前现场验收。

v9审计发现“编排引擎有了，仪表盘没有”：配置能工作，但用户缺少直观设置界面。它补团队配置、每位置模型/推理等级、控制面插件、本地面板和保护性安装/回撤。v9 README明确该包当时未安装，并列82测试及合同检查等观察范围；不能把代码生成说成已经普遍部署。这个阶段也解释了后来为什么必须把前台操作纳入架构验收。

## 9月20—30日：走向跨宿主连续性内核

现有证据不足以为这一段逐日还原每次运行，保留日期空白。9月30日DB1.1总览/细节文件已明确PORTUS/UACF方向：统一Project、Task、Session、Evidence、Decision、Failure、Validation、Artifact与Provenance，宿主可以替换，前台/连续性运行时/后台共享一个状态权威。目标从“装好一个DSH工作台”变为“工程跨会话、跨模型、跨宿主仍能接续”。这份概念文件的修改日期是线索，不能自行证明所有设计已部署。

## 10月1日：E0—E2形成可运行的规范核心

私有Git首批实现记录把对象合同、认证State Service、修订、证据与备份恢复落为程序；DSH连续性和离线恢复按冻结环境验收。权限、expected_revision、operation_id与唯一canonical权威开始成为执行约束，而不是靠聊天中的提醒。原件/历史与可重建索引分开。

## 10月2—3日：E3/E4话语解释、来源与受控执行

E3/E4增加有界来源、分支/引用/修辞解释、Claim与AdoptionDecision、任务上下文、预算与路由，以及统一控制界面。历史AI文字和讨论只能作为候选，当前直接用户指令才可采纳。第三批继续本机隔离交换与接续，第四批把费用/未知请求和实际派发约束串起来。附件定位与附件正文分别记账。

这也是命令架构的关键出处：底层已能区分原话、解释和采纳，但不代表每个实际长任务都把全部要求接进了稳定命令通道。后来的遗漏暴露的是接线与验收没有做好，不能把“有这些类”说成用户要求已持续有效。

## 10月4—5日：补充03、兼容性、真实宿主与前台

五项工作把基础修复、有限开源研究、设计补充、宿主接入、真实实验及公开发布分成有依赖的合同。补充03收束规范；生态兼容、真实宿主项目/性能与E7状态UI留下单独交接。Wing/Strata等概念研究不等于引入它们的运行代码；撤销/排除实现以最终决定为准。浏览器会话持续使用、认证、状态回读、宿主映射等问题需要现场结果，不能继承历史成功。

## 10月6日：E7结构归档与900详细候选

2531来源完成冻结范围内结构归档；其中900完成公开正文详细提取，生成3793知识候选及1980问题/边界实例。结构、提取、语义判别与专业真值四层分开。相关727和条件扩展274是提案标签，不能视为确认合并或独立错误数量。

## 10月7日：学习接线、语义/UI修复及分层分享

151对审查涉及115实例；全量语义并未完成。工作更新链、旧经验准备/送达/使用、真实宿主公开回读、条件与前台展示继续修复。增加本地私人来源与公开抽象模块两层，支持复用既有候选补做脱敏；整理触发按重要纠正、变化、进展、结束与闲置分开，短补充聚合，轻量检测不再发一个模型请求。说明与安装入口转向普通人可用的双语交付。

## 10月7—8日：首批新100、公开版与本次纠正

后续独立20元授权下，100公开来源完整提取、21完整来源风险复核约9.9936%正文、候选发布完成，回执费用上界4.406337元。全部100进入共享队列，21来源已回填，79待共享语义分类；没有把候选当领域真值，没有重提取900。

Apache-2.0干净公开版发布，排除私人Git历史/资料/本机绑定和未获许可实现，增加完整说明、操作手册、补充04与阅读入口。随后用户指出：命令保留不足、历史正文遗漏早期内容、合规章节像要求转述、资产意见缺少人可读交付。本次据旧代码与实际来源修正：独立命令记录、追加/订正/重复/未决生命周期、注册入口的重复停止与真实重准备、人可读原则与条件对比前台。现场通过范围以本次验收报告为准，不由这段历史自称完成。

## English chronology

September15–16: an installable DSH research workbench and PowerShell compatibility fixes. September17: Codex delegation, egress checks, plugin audit and foundation hotfixes. September18: deterministic recovery and v7–v7.4 governance with real repeat denial, checkpoint/path controls and corrected experiment identity. September19: v8 orchestration, then v9 configuration/UI control-plane work, with generated versus installed explicitly separated. BySeptember30: the PORTUS/UACF cross-host continuity kernel. October1–3: authenticated canonical state, evidence/revisions, discourse/adoption and controlled routing/budgets. October4–5: Supplement03, compatibility and real-host/UI contracts. October6:2531 structural sources and900 detailed candidate extractions. October7: learning, pair review, bounded capture and public/private lesson separation. October7–8: staged100 candidate publication, clean Apache release, then correction of instruction retention, chronology and human-readable opinions. Package self-reports and file times are evidence categories, not universally verified runtime facts.
