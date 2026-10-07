# UACF 第二阶段整体运行与操作模式

## 当前阅读说明 · 2026-10-08

本项目已公开发布，Apache-2.0由所有者选择。当前正文按发布结果修订；旧现场补记移入末尾历史附录，不能当成当前待办。源码与干净安装各187测试通过。新100的完整公开正文处理、约10%正文宿主复核和候选发布完成；100份加入共享链，21份已有宿主分类回填，79份继续待共享语义分类。旧900全量语义审查、附件/领域真值、任意工具控制和所有宿主现场自动回调未宣称通过。完整阅读入口见《UACF_阅读导航》，冻结状态见Release与VERIFICATION。

2026-10-08｜第二阶段公开版操作说明｜中文 / English。本文说明实际操作、当前结果及仍需独立验收的范围；文件身份以Release清单为准。旧设计及历史报告保留。

## 1. 对使用者来说，它做什么

UACF帮助你在AI协作中保存“我要做什么、做到了哪里、哪些要求还没有满足、旧经验在什么条件下能用”。你可以做科研、写作、视频或日常项目，不必先把工作改写成编程任务。前台让你查看项目与任务、来源、知识/错题候选及验收；中台连接任务、执行、复核和费用；后台保存原件定位、规范修订和证据。

它不能保证AI不会再犯错。已召回的错题是否符合本任务、是否送达宿主、是否实际用于结果，需要分别观察。候选不是事实；结构归档不是历史全文理解；hash确认身份和字节，不验证私有思考。

English: UACF preserves work intent, progress, source-linked lessons and acceptance evidence. It supports research, writing, media and ordinary projects as well as software. Retrieval, delivery and actual use are different states. A candidate is not an accepted fact, and a hash does not verify reasoning or semantic correctness.

## 2. 第一次开始

本机已有常设前台时，打开本机服务页面，确认是自己的工作根与authority。首次浏览器配对只在本机完成；之后按会话有效期恢复。不要把认证文件、配对票据或本机绑定上传到社区。页面离线、未配对、会话过期和任务溢出都有不同处理原因。

下载Release完整ZIP并全部解压，双击“开始使用UACF.cmd”或Start-UACF.cmd。启动器寻找CPython3.11、按锁定hash安装官方依赖并打开本机前台；Codex/Pi/DSH分别有Install-for-*.cmd配置入口。已有Python环境的干净安装已测试；缺Python的官方引导分支未在本机实际触发，不宣称任意新机器均已验证。空库真实0来源，普通任务不要求DeepSeek、DSH或旧batch4账本。

维护安装命令的现有参数是 `ops/install_public.ps1 -Root <你选的工作根>`；服务启动、停止和状态由 `ops/manage.ps1` 提供。这是技术维护入口，普通使用者不应每天重复安装。选择端口时遇到占用，应明确失败，不终止别人的进程。

English: use your own local service and pair the browser locally. Never share credentials. The full release ZIP includes Start-UACF.cmd and preserving Codex/Pi/DSH setup helpers. The Python-equipped clean path was tested; the missing-Python bootstrap and all real native-host environments are not universally verified. Ordinary tasks must work without a paid provider, a historical account or private data.

## 3. 建立工作：先明确任务，再开始执行

把目标、输出形式、必须完成的工序、适用限制和费用授权写进当前Task。比如“整理实验图并给出可追溯结论”，至少应明确图从哪里来、什么范围可以分析、未读取附件怎么办、要交付哪些文件，以及什么证据能证明完成。

准备上下文时读取当前修订的ready capsule。普通工作使用正在工作的宿主，不为了检查再开一次GPT。DeepSeek是明确选择的外部路线；有新付费派发时绑定Task、账户、路由、价格和预算，不借用其他专项余额。当前修订不一致或必需上下文溢出时，要修合同或分段，不能删去核心要求继续执行。

原要求未完成时，新补充默认是同一工作中的修正。先将补充纳入合同，检查上一步遗漏与相关旧资产，再继续。不要因新要求很多而改做旁枝，或用处理数量替代用户关心的闭环。

English: define the intended deliverable, required steps, constraints and evidence in a current Task. Prepare a ready capsule for that revision. New instructions normally steer the ongoing work. Do not silently replace the main objective with easier work. Paid routes require an explicit account and authorization.

## 4. 旧知识和错题怎样用于当前工作

在前台“错题与知识怎样用于工作”入口选择当前Task，准备相关候选。先读原则、适用条件、排除条件和原条件；需要具体判断时才展开确切来源。模型版本是检索提示，不把通用约束限定为某个旧模型。

检索分数只是找到可能相关的材料。不同表述但条件相同可提出等价链接；共用原则但条件不同应保留分支；同样报错字样但原因不同、同模板但问题独立，应分开；无法判断则未决。语义待审区和已审区分别显示；只有字段相等或复制同一记录的识别不构成真实语义审查。

准备回执记录候选集合和修订；送达需要真实宿主调用/公开上下文证据；实际使用需要结果或工具记录与适用条件的对应。不要把“已展示”按钮当“AI已采用”。注册的有限执行约束只约束具体入口与验收，不代表任意工具和私有思考均受控。

English: inspect the principle, applicability, exclusions and original conditions. Search scores locate candidates; they do not decide equivalence. Keep conditional branches and independent problems. Preparation, host delivery and demonstrated use need separate evidence.

## 5. 工作进行时何时整理

不必等一个工程永远结束才学习。适合轻量增量整理的节点包括：用户明确要求整理、确认的重要遗漏/纠正、实质需求变化、积累到可解释的工作进展、用户明确满意或结束。强烈语气可提醒关注当前指令，但单凭情绪不能判定AI错误或推断人的心理。

很短的生活化问答通常只保留必要元数据；多个中途补充应合并到同一工作节点，不逐句重新提取。长时间未调用的项目要作到期检查，先看最后工作时间、最后整理时间、当前任务及未决状态，不直接全文重读或收费重跑。

**现场边界：**已有重要检查点与部分原生结束事件入口；综合时间、节流、信号聚合的新增代码目前仅生成，未接入当前运行服务、前台和完整测试。当前桌面正常结束自动回填仍partial。结构化最小提示与零额外模型的检查应经实测后才称可用。没有账户连接时，不声称能自动遍历所有云对话。

English: capture meaningful work nodes, not every sentence. Explicit corrections, changes and satisfaction matter more than text volume. Stale work requires a bounded metadata check. The current installation has checkpoint and partial native-event paths; the newly generated adaptive policy is not yet deployed or verified.

## 6. 正常结束与同一资产链

真实授权、映射的宿主公开输入/输出/工具/结束事件才能形成正常工作来源。来源经同一链生成知识与问题候选，进行语义比较，保留关系和条件，再建立可重建索引。原生工具canary不是完整模型回合；手工记录不是自动宿主捕获；工作任务自己宣称完成不是验收。

结束前核对所有必需工序、未决、费用和返工。保存结果文件、回执及结束切片，备份到新的目录。恢复验证使用隔离库，暂停外部与付费派发；不回滚实时数据，不自动重放未知结果或请求。

English: only real, explicitly mapped public host events establish native work sources. Run them through the same candidate, semantic comparison, relationship and indexing chain. Use an isolated recovery test and preserve live history. A canary or an assistant's completion claim is not full workflow acceptance.

## 7. 历史资产与新来源处理

先核对最新覆盖清单，冻结真正未处理的来源和验收范围。2531对话的结构归档与900来源的详细候选分别统计。900不是通用系统上限，也不是新任务的假基线。旧成功输出可复用；未知、reserved、dispatched、response_known先对账，不换模型重跑。

新批次分阶段推进。当前允许最多100新来源用于检验最新架构，拟设10、30、60、100检查点；闭环、隐私、规范对象/前台一致性或费用失败时停止新增。所有者随后授权独立20元账户；100来源已完成完整公开正文处理和候选发布，21份完整来源风险复核占9.9936%正文，回执费用上界4.406337元。新的150实际检测未执行；其早期冻结准备保留。附件、领域真值及全量成对语义审查仍分别待验，不能把候选发布替代这些验收。

附件没读、领域事实没验收应明确显示。归档是否完整、候选是否忠实、语义是否正确、领域真值是否成立，是四个独立问题。

English: freeze uncovered sources from the latest manifest. Reuse settled outputs and reconcile unknown requests before retries. The owner subsequently authorized a separate CNY20 account. All100 frozen sources were processed and published as candidates;21 complete-source reviews covered9.9936% of public text. The observed fee upper bound is CNY4.406337. Candidate publication does not certify domain truth or full semantic review.

## 8. 本地资产怎样变成可分享模块

本地层保存真实来源、修订、判断依据及读取权限；公开层只保存抽象原则、明确适用/排除条件、合成正反例、限制与版本。公开包没有私有UUID、聊天引文、路径、模型私人标签和凭证。两层通过本地注册表关联，公开模块更新后仍能在本机查来源，别人收到模块不因此得到私有库。

已有候选的脱敏应复用其既有结果，按当前修订补做投影与来源链接，不重提取900。新增候选走相同流程。先由当前宿主审查具体投影，再由用户审批实际公开范围；机械秘密扫描不能保证彻底脱敏。模块不是自动新硬规则；真正执行约束还需注册、门控、正反例和验收。

**实现状态：**分层模块已接入服务、上下文与前台；草稿导入、精确版本复核、来源条件回读与公开投影导出经过实际调用。三个抽象原则已纳入公开包，私人来源链接保留本机。旧候选无需重提取即可补做模块投影；这不表示900全部实例均已脱敏或全部模块均已独立验证。旧包保持原样，本版按实际新清单冻结。

English: maintain a private provenance registry and a separate reusable public projection. Reuse existing settled candidates for backfill. Public cards contain abstract conditions and synthetic examples, not private source identifiers. The module path is integrated and actual draft import, review, private-source read-back and public projection export were exercised. Three abstract advisory lessons are included; the entire historical library has not been sanitized or independently accepted.

## 9. 遇到问题与退出

页面数字异常时对照规范对象和队列；不要直接改SQLite修数字。服务报错时保留回执并检查当前authority/schema、源码/安装/加载身份。规范修订使用认证State Service、operation_id和expected_revision。未知费用保留未知，不记0。

卸载先移除自动启动注册，再停止自己的服务，按对应安装范围移除组件；保留data、原件、备份和历史。新机器重建只安装锁定且明确来源的依赖，不带私人配置、轮子仓、原始ZIP或旧.git。发布前审查文件白名单、许可、引用和能力缺口，审批后再上传。

English: use authenticated commands, not direct SQLite writes. Preserve unknown costs and operation receipts. Remove startup registration and stop only your own service before uninstalling components. Keep user data and history. Publication requires review of the exact clean export and licensing scope.

相关阅读：正式总说明、补充04、早期迭代说明；维护合同与实际回执在engineering和本地deliverables中。公开发行时只收录经审查的说明，私人回执不随包分发。



## Historical appendix / 历史补记（不是当前状态）

以下为原日期下的状态，保留供追溯。For current behavior, use the main text and verified release scope.

## 2026-10-07 继续执行后的状态修订

前一检查点仅生成代码与文档，不能算五项要求完成；本节保留并修正其验收边界。现已接通认证State Service、Task context、现有前台与周期元数据检查；实际部署身份前缀32be59b945e4，安装与加载需分别回读。前台实际审查三个旧病例派生的双语指导模块，保留本地私有来源映射，公开导出仅含抽象原则、条件和合成正反例。没有重提取已结算900来源，没有合并原病例，没有新增执行硬规则。

当前宿主context实际返回两条脱敏指导，私有来源链接未送达；这证明本次准备与送达，不证明每次工作实际采用。触发策略默认零额外模型请求，以结构信号、冷却、合并与过期元数据检查控制频率。真实正常结束的自动回填仍缺当前Task原生事件映射/送达验收，不能将手工注记或测试事件当正常工作。

完整回归160项通过；新增宿主配置助手5项独立测试通过。新增中英文完整用户手册及解压后双击入口；已有Python环境的安装路径与缺Python的官方安装分支分别验收，后者尚未现场执行。Codex/Pi/DSH助手配置成功不等于宿主已加载；DSH离线依赖失败时新建配置仍保留供检查，不能声称所有状态已撤销。

100新来源仍仅冻结准备、实际新增0，闭环与具体金额授权未完成，未启动外部付费派发。最终公开源码和三个脱敏模块仅作为本地候选；项目许可、人工隐私/来源许可审查和GitHub上传批准尚未取得。新候选隔离安装结果以最新报告为准，不能继承旧候选安装成功。


## 2026-10-07 本次继续执行的最新现场范围

本页较早章节保留当时状态，最新事实以本节及最新冻结回执为准。Apache-2.0已由所有者明确选择，完整英文总设计及完整中英文用户手册均已产生。新增普通人说明“900之后架构到底改变了什么”，分别说明五类有限注册门控、原则与条件分支、上下文候选与实际采用；系统没有普遍的“三次失败便强制阅读架构”门控，不把建议冒充已实现能力。

三个可分享原则保留本地私有来源映射。前台已实际读取核心工序遗漏投诉的原条件；新增导入入口保存为草稿，未经复核禁止导出和进入任务上下文，复核后才作为有条件指导。公开模块不包含旧900私人正文，也不自动安装硬规则。Windows冷启动实测发现后台服务继承管道导致入口等待，修复后冷启动成功返回；内嵌浏览器文件选择器崩溃仍记录为宿主限制，另提供粘贴公开JSON方式并完成真实前台导入回读。导入按钮遗漏规范操作字段的问题已经实际发现、修复和回读。

当前明确映射的Codex聊天已通过官方只读公开接口读取真实前轮结束状态，公开输入、输出及工具记录进入同一来源→候选→语义比较→回填链，没有另开GPT推理，没有伪造结束事件。此为公开回读传输，不能称原生live hook已通过；正在执行的本轮正常结束仍等待真实事件，账户全部聊天和任意宿主自动捕获未验证。周期元数据扫描已经修复超过64任务时后续任务永远得不到检查的问题，按有界游标轮转，检测不额外调用模型。

新100精确冻结，与既有900覆盖不重叠；所有者授权独立人民币20元账户，旧账未扩大。正式第一段10个来源已完成完整公开正文提取，尚未全部完成复核、回填与发布，因此新增已发布覆盖仍为0。检查发现外部提取只检查上下文却未送出旧资产指导，已经暂停后续来源并修复后续请求送达代码，旧已结算输出保留复用。不能把这10个提取成功写成100验收完成，也不能把模型自称采用当实际使用证据。附件未读、历史领域真值和独立语义验收仍有边界。

源码回归177项曾完整通过。更新的干净候选安装和空库前台已实际运行，空库真实显示0来源和0历史候选；随后同177项测试的一个Windows临时服务清理失败已修复，相关4项重新通过。后续代码修订仍需新冻结和相关复测，不能继承旧包hash。未知费用、许可缺口、原生宿主加载与自动结束状态按最新回执分别保留。GitHub条件授权已收到，但实际Firefox页面捕获失败，不能确认账号登录，当前没有上传。


## 历史验收补记 · 2026-10-07 14:00 UTC

最新公开候选干净安装的178项测试全部通过；已复核合成模块的导入导出、全部当前宿主的普通任务计划、隔离备份恢复通过。卸载核对保留数据；没有部署指针时是幂等空操作，不能据此宣称已恢复真实宿主配置。真实宿主加载、live hook和当前正常工作结束仍为partial。现场大库部署校验仍在途。新历史来源提取10个，完整复核和发布均为0；架构检查点失败后停止新增。23个请求已结算，按高峰价核算的用量费用上界0.768499元，供应商账单仍未知。项目许可证Apache-2.0；尚未上传GitHub。


## 本次最终冻结范围 · 2026-10-07T22:16:14.812604+00:00

本节是本版当前验收范围。前面按日期保留的补记是历史状态，不能当当前结果；旧版文件另有保留。本阶段完成正式中文总说明、完整英文总设计、双语用户手册、第二阶段运行模式、补充04和早期迭代说明。发布采用Apache-2.0与干净初始公开历史，保留私有工程的全部原历史。

源码187项测试通过，干净官方依赖安装后187项也通过。空库初始化当前schema，真实前台显示0来源、0候选、0问题，不生成旧batch3/batch4授权账户；没有DSH、DeepSeek或本机旧账仍可运行普通当前宿主任务。真实代码部署指针的卸载保留数据库hash，隔离恢复生成另一authority、完整性通过且不重放外部动作。合成隔离宿主配置经真实Codex配置解析和比较后卸载恢复；这不代表在所有真实宿主环境卸载都已验证。

边工作边整理现已在这个明确映射的真实聊天验证：读取已有正常结束与公开事件，当前工作节点生成来源、候选、语义比较和同链回填；后续节点按前一真实来源边界增量捕获68条新公开记录，未重复最初用户要求，检测与当前宿主回填不另启动GPT。未知观察已认证对账，复用原来源，不重放原工作。低成本结构信号识别明确请求、纠正、实质需求变化、满意、结束与长时间闲置，短日常工作和只有上下文数量增长不会自动扩大整理。元数据检查轮转，不通读全账户聊天。公开只读回读不是原生live hook；未映射的任意宿主、当前尚未发生的最终结束、账户全量扫描仍不宣称verified。

新100与旧900无覆盖重叠，全部公开正文2,417,919字符已处理并规范发布为候选；当前宿主复核21个完整来源，正文占比9.9936%，按10/30/60/100检查点保留回执。旧900未重新提取，旧2531结构归档与详细候选覆盖分别记数。旧900的1980问题/边界实例并未完成全量语义重复审查；新100发布也不等于领域真值或所有附件理解。语义比较待审、已审、同原则链接、条件分支、独立和证据不足分别记录，检索分数或机制族不能批准合并。

旧资产指导在后续外部请求中实际送达并有prompt身份回执，宿主复核按原条件应用：德语已满足时排除误报、英文注释与正文语言分开、跨函数返回合同与变量时间语义分别核对。模型自称采用不作为验收。首10旧指导送达缺口保留，不倒写成功；已结算格式错误复用原输出修正，未重新付费。检测没有生成新增硬规则，共同原则仍一份定义、实例独立链接。现有五类注册门控只限制其实际接入的执行/交付边界，不控制私有思考或任意Codex工具；普遍“失败三次强制回读结构”尚无对应全宿主执行门控。

三条已复核脱敏原则支持新草稿与旧资产回填，本机来源映射单独保留；公开模块仅包含抽象条件及合成例子，不含私人900/100正文、原附件、真实来源ID、凭证或本机绑定。费用按现有回执高峰价上界4.406337元核算，独立授权20元未突破，供应商账单金额仍未知，不记0。
