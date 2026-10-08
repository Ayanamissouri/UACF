# UACF — 让AI工作保留要求、来源和经验

UACF 是一套跨模型、跨会话、跨执行环境维持智能体任务与项目状态连续性的统一基础织体。

UACF 面向科研、写作、视频制作和工程工作。它在本机保存任务与资料，帮助AI按当前任务取用旧经验，并把新工作的公开结果、纠正和条件送回同一资料库。它不会保证AI永不犯错，也不会把私人聊天自动公开。

先双击包内 **阅读说明.html / Read-UACF.html**，或打开[完整阅读导航](repo/docs/baseline/UACF_阅读导航.md)与[逐项交付核对](repo/docs/baseline/UACF_交付要求逐项核对.md)。本次文档修订将过时现场状态移入历史附录，当前说明在前。

## 不懂编程也可以开始

1. 到本仓库的 Releases 下载完整 ZIP，解压到你希望长期保存资料的文件夹。
2. 双击 **开始使用UACF.cmd**。首次安装使用官方Python依赖；随后打开本机前台。
3. 先阅读[中文用户手册](repo/docs/baseline/UACF_普通用户使用手册_中文.md)。普通任务默认使用当前AI宿主，DeepSeek是需要预算授权的可选路线。
4. Codex、Pi、DSH用户可使用对应的 Install-for-*.cmd 配置入口。安装配置、宿主加载和实际调用是三个不同状态，不能用安装成功代替实际调用验收。

不要把下载目录里的代码当成你的资料备份。私人原件、数据库、宿主令牌和真实来源链接留在本机；分享经验时，只导出复核过的抽象原则、适用/排除条件和合成例子。

## 读懂这套系统

- [正式完整中文设计总说明](repo/docs/baseline/UACF_正式完整版设计总说明.md)
- [第二阶段运行与操作模式](repo/docs/baseline/UACF_第二阶段整体运行与操作模式.md)
- [补充04：原计划到当前实现的变化](repo/docs/baseline/DSH_第一阶段设计补充04.md)
- [900个来源之后，架构到底改变了什么](repo/docs/baseline/UACF_900之后架构到底改变了什么.md)
- [验证范围与限制](repo/docs/public/VERIFICATION.md)
- [参考、许可与排除范围](repo/REFERENCES.md) · [第三方说明](repo/THIRD_PARTY.md)

## English

UACF preserves requirements, sources and conditional lessons for research, writing, media and engineering work. Download the release ZIP, extract it into a persistent local folder, and run **Start-UACF.cmd**. Read the [English user guide](repo/docs/baseline/UACF_User_Guide_English.md) and [complete English design](repo/docs/baseline/UACF_Complete_System_Design_English.md). The default route uses your current host; optional external models require explicit authorization and a budget.

Private originals, databases and provenance links remain local. Shareable modules contain reviewed abstract guidance and synthetic examples. Guidance is not an executable rule. Verified claims apply only to the documented release, environment and test scope.

Licensed under Apache-2.0. This release contains a clean initial public history; it excludes the private project's Git history and personal assets. Contributions should include conditions, counterexamples, permission to share, and evidence of the actual scope tested. See [CONTRIBUTING](repo/CONTRIBUTING.md) and [SECURITY](repo/SECURITY.md).
