# References and acknowledgements / 参考与致谢

## Stop That Shit — MIT

[Repository](https://github.com/lennney/stop-that-shit) · [reviewed commit 3929e2df30ac299a1de25a155d2ac8b3f354952b](https://github.com/lennney/stop-that-shit/tree/3929e2df30ac299a1de25a155d2ac8b3f354952b) · [architecture](https://github.com/lennney/stop-that-shit/blob/3929e2df30ac299a1de25a155d2ac8b3f354952b/ARCHITECTURE.md) · [evidence](https://github.com/lennney/stop-that-shit/blob/3929e2df30ac299a1de25a155d2ac8b3f354952b/EVIDENCE.md).

UACF 的动作前模式/路径控制、Stop Ladder 责任与有效防御判断，以及 STSS 减少无用防御性文字的原则，参考了 STS 设计。UACF 保留自己的任务、来源、修订、预算和验收机制。本次没有打包上游运行时或 Skill 实现。

UACF's action-before mode/path policies, Stop Ladder responsibility/useful-defense judgments and STSS guidance against needless defensive prose draw on STS design. UACF retains its own tasks, provenance, revisions, budgets and acceptance. This update does not bundle the upstream runtime or Skill implementation. Upstream tests distinguish deterministic/native-host behavior from general model effectiveness.

## DeepInfer — Apache-2.0

[Repository](https://github.com/deepseek-ai/DeepInfer) · [reviewed commit a679bb86ce36e883a98a97733492b686e5b9a08e](https://github.com/deepseek-ai/DeepInfer/tree/a679bb86ce36e883a98a97733492b686e5b9a08e) · [LLMEngine](https://github.com/deepseek-ai/DeepInfer/blob/a679bb86ce36e883a98a97733492b686e5b9a08e/deepinfer/engine/llm_engine.py) · [scheduler](https://github.com/deepseek-ai/DeepInfer/blob/a679bb86ce36e883a98a97733492b686e5b9a08e/csrc/engine/scheduler.hpp).

异步调度、准备与执行的分离、输出确认和资源生命周期作为结构性参考，用于 UACF 中台执行与后台索引协作。DeepInfer 是推理引擎，不能直接被描述为档案库；本次没有嵌入或运行其 GPU 引擎，也没有重分发其实现。

Asynchronous scheduling, preparation/execution separation and output/resource lifetimes serve as structural references for UACF execution and background indexing. DeepInfer is an inference engine, not an archive implementation. This update does not embed/run its GPU engine or redistribute its implementation.

These design references do not imply upstream endorsement, universal language reliability, or automatic enforcement on every host.
