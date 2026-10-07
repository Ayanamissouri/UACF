# 架构总览及冻结边界

## 从工作到资产

用户意图 → TaskContract修订/工序/权限 → 任务相关资产准备 → 明确宿主映射及公开调用 → Evidence/Attempt → 注册Validation → 有限采纳与交付。

公开来源或真实工作事件 → 来源绑定候选 → 检索邻居 → 当前宿主比较原则与适用/排除条件 → 等价链接、共享原则的条件分支、独立问题或未决 → 可重建索引 → 下一工作准备、送达、实际采用、再验收。正常结束事件未观察时停止自动闭环声明；不伪造Stop或工具结果。

前台apps/control-surface显示来源/AI分类回执、知识与错题去向、规则作用位置、待审/已审语义关系和原条件。中台Task/ResponseContract/角色/采纳状态表达授权与验收。后台来源、Evidence、版本与immutable blob保存证据。全部规范写入经认证State Service、operation_id幂等与expected_revision/CAS；SQLite不是另一个写入口。

## 四层资产

|层|用途|不可推断|
|---|---|---|
|知识上下文|按任务检索的提示、经验|召回就表示已采用|
|信息引用|带定位的原公开输入/输出/附件状态|未读附件也已核验|
|语义原则及条件分支|共享一份原则，保留实例适用、排除、纠正与关系|粗机制族、字符串相似或hash即语义相同|
|已注册可执行约束|有限执行/交付边界，正反例与注册Validation|任意Codex工具或私有思考已受控制|

hash只锁身份、修订、环境与文件。语义判断和领域真值需要相应证据；hash不验证私有思考，不代替理解。

## 验收范围

generated是文件/对象已产生；installed是安装副本存在；loaded须有本轮进程身份；called须有实际调用回执；verified仅适用于冻结的性质与反例；partial表示仍有明确缺口。源码存在不等于运行已用。

旧2531对话的冻结结构归档，与900来源的详细候选提取分开。900提取产生3793知识候选/1980问题边界实例；既有151对语义审查涉及115实例，1865旧实例未有此类审查。727相关/274扩展只是候选关系。后续当前工作纠错新增一来源/一知识/一问题，不算新增历史覆盖。当前新150只是未付费冻结清单，处理0，未产生检测交接。

旧病例六组回归涉及德语首答、端口分支、不同代码根因、金融与硬件独立问题、未读附件边界；已知旧判断的回归不算盲测或独立领域验收。当前全量语义仍partial。

## 工作时机与宿主

重要遗漏纠错、需求变化、里程碑、用户满意/结束是聚合信号；同工作补充合并处理。短日常默认轻量，不按情绪、文字长度或每条短句制造错题。宿主未提供可信公开事件时只能保存明确授权的手动来源，不能声称自动捕获。长期闲置自动归档缺账户活动连接，partial。

MCP公开声明context/status/asset_read/learning_next/learning_submit五工具。显式工具与生命周期hook是两条路径；安装hook、工具canary或SDK刺激不算正常模型回合。Pi/DSH历史有限实际工程试验有回执，当前任意宿主、云ChatGPT及真实远端全自动接续未验收。Knowledge检索按Task，模型版本只作提示；通用约束跨模型复用。

注册约束包括来源引用、当前修订验收、预声明文件保护、未知回执禁止重派发、声明工序验收。这些是有限机械性质，不能自行把候选文本变执行代码。

公开DSH包使用public.js，仅连接通用context/status/asset_read/learning队列与既有显式映射生命周期。旧付费工程试验、固定旧对象纠正脚本和其执行器全部排除；公开入口的声明测试不是已安装/已加载/真实模型回合验收。

## 公开版与本机专项编排 / Public and private orchestration

公开版包含普通任务、原生工作来源、候选回填、语义待审和脱敏模块链。旧900及本轮100的私人专项编排脚本不分发；不能把其本机批次回执当作公开包已包含同样的私人批处理入口。前台可读工作状态，通用更新走公开的原生工作入口；需要旧专项编排时明确显示缺连接。
The public release contains the ordinary-task, native-source, candidate-return, semantic-review and sanitized-module chain. Private orchestration for the old900 and this100 is excluded. Its local receipts do not prove that the public package includes that private batch runner. Missing optional connections must remain explicit.
