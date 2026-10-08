# UACF 阅读导航 / Reading hub

2026-10-08。你可以只读前两份来开始使用，再按需要阅读完整设计。所有手册的当前说明在前，旧现场补记在末尾历史附录。HTML版可以直接双击打开，无需安装或启动服务；Markdown版可在GitHub阅读。

Read the first user guide to begin, then consult the full design as needed. HTML documents open locally without a running service; Markdown documents are readable on GitHub. Current behavior comes before preserved historical notes.

|建议顺序 / Order|文件 / Document|阅读目的 / Purpose|
|---|---|---|
|1|[先看：900之后架构到底改变了什么](UACF_900之后架构到底改变了什么.html) · [MD](UACF_900之后架构到底改变了什么.md)|用普通语言看系统能做什么、哪些仍有限制。|
|2|[普通用户中文手册](UACF_普通用户使用手册_中文.html) · [MD](UACF_普通用户使用手册_中文.md)|安装、前台按钮、开始任务、旧经验、纠正、历史处理与分享。|
|3|[完整英文用户手册 / English user guide](UACF_User_Guide_English.html) · [MD](UACF_User_Guide_English.md)|Full installation and screen-workflow instructions; not an English abstract.|
|4|[正式完整版设计总说明](UACF_正式完整版设计总说明.html) · [MD](UACF_正式完整版设计总说明.md)|完整设计框架、工作原理、三层结构、规范权威与验收边界。|
|5|[完整英文总设计 / Complete system design](UACF_Complete_System_Design_English.html) · [MD](UACF_Complete_System_Design_English.md)|Full architecture, objects, control, learning, privacy and recovery.|
|6|[第二阶段整体运行与操作模式](UACF_第二阶段整体运行与操作模式.html) · [MD](UACF_第二阶段整体运行与操作模式.md)|按真实任务生命周期理解前台、中台、后台和同链回填。|
|7|[补充04：原计划到当前实现](DSH_第一阶段设计补充04.html) · [MD](DSH_第一阶段设计补充04.md)|说明第一阶段之后增加、修改及尚未全面验证的内容。|
|8|[带日期的早期迭代说明](UACF_从早期工作台到当前流程的迭代说明.html) · [MD](UACF_从早期工作台到当前流程的迭代说明.md)|早期工作台、迁移登记、阶段设计、部署、900和发布的证据日期。|
|9|[交付要求逐项核对](UACF_交付要求逐项核对.html) · [MD](UACF_交付要求逐项核对.md)|对应提出的要求、实际交付位置、已验范围与保留缺口。|

## 安装与开始 / Install and start

从[完整ZIP下载页](https://github.com/Ayanamissouri/UACF/releases/latest)下载UACF完整附件，而不是只下载GitHub自动生成的Source code。全部解压并保留repo文件夹，双击“开始使用UACF.cmd”或Start-UACF.cmd。需要宿主接线时选择Install-for-Codex.cmd、Install-for-Pi.cmd或Install-for-DSH.cmd。首次依赖准备需网络；缺Python与宿主实际加载分别按现场检查，不能继承本机成功。普通任务默认当前宿主，不要求DeepSeek或旧账本。

Download the complete UACF ZIP asset from Releases, extract the whole package, retain repo and run Start-UACF.cmd. Host setup helpers are optional. First installation needs network access; missing-Python and actual native loading remain environment-specific checks. Ordinary work uses the current host and needs no paid model or old ledger.

## 维护、引用和社区 / Maintenance and community

- [安装、停止、卸载、隔离恢复](../public/OPERATIONS.md)
- [当前验证范围](../public/VERIFICATION.md)
- [公开/私人链路架构](../public/ARCHITECTURE.md)
- [GitHub上传和后续更新方法](../../UPLOAD-GUIDE.md)
- [参考思路及最终采用边界](../../REFERENCES.md)
- [第三方依赖](../../THIRD_PARTY.md) · [许可缺口](../../LICENSE-GAPS.md) · [NOTICE](../../NOTICE.md)
- [贡献说明](../../CONTRIBUTING.md) · [安全说明](../../SECURITY.md) · [变更历史](../../CHANGELOG.md)

原始第一阶段总览及补充01—03保留在所有者私有设计目录；公开版以补充04、迭代说明和当前完整设计解释其关系。旧包、私人数据及未获许可实现不因透明说明而重新分发。三个公开经验模块含抽象原则与合成例子，私人来源链接只留本机。全部900的语义审查、全部附件和领域真值未完成，不能从候选数量推导已验证能力。

The original first-stage documents and private history remain preserved locally. Supplement04 and the migration account explain the public lineage without redistributing private or excluded material. Three advisory modules contain abstract conditions and synthetic examples. Private provenance stays local; full old900 semantic review and domain truth remain separate from candidate publication.


[10月8日七项问题修正与实测说明](UACF_七项问题修正与验收说明.html)
