# GitHub公开发布与经验更新 / Publishing and guidance updates

所有者已选择Apache-2.0，实际账号授权已核验；项目现已公开发布在[ Ayanamissouri/UACF ](https://github.com/Ayanamissouri/UACF)。从[最新Release](https://github.com/Ayanamissouri/UACF/releases/latest)下载完整UACF附件。第一次公开发布只建立干净初始历史；后续审查版本在同一公开仓库正常追加提交，保留过去Release，不上传私有旧.git。

## 不会写程序也可以分享经验

先在本机“可分享经验与本地来源”制作或导入草稿，阅读条件、限制和合成例子，复核具体修订，再“下载此版公开候选”。检查输出没有私人原话、来源身份、本机路径、联系方式、凭证或罕见可识别经历。不要上传“查看本地来源”的私人响应。

打开本仓库Issues，提出“脱敏经验建议”，说明原则、适用/排除条件、合成正反例、实际观察与未验证范围；只附审查过的公开JSON。发布前核对你有权分享这些内容。维护者会检查许可、语义关系和条件；提交不等于自动采纳、领域真值或新硬规则。没有GitHub账户时，可把经过审查的通用模块交给你明确授权的协作者，不需要发送整个资料库。

English: export an exactly reviewed advisory module, inspect its privacy and permission, then submit a sanitized proposal through Issues with conditions, synthetic examples and known limits. Never attach the private provenance response or raw conversation/database. Maintainer review precedes adoption; contribution does not establish domain truth or executable enforcement.

## 由安装助手或维护者更新代码

核对PUBLIC-MANIFEST逐文件清单、EXCLUSIONS、NOTICE、THIRD_PARTY、SBOM和LICENSE-GAPS。保持私有工程/历史原样，使用独立干净导出。代码变化要新冻结和相关复测；仅文档变化核对正文、链接、公开隐私范围及运行代码hash未变。只有明确授权的公开变更进入公开分支，不force push私有旧历史。保留旧Release，发布新版本的完整ZIP和SHA256，下载回来验证hash，并确认GitHub远端HEAD/清单。

禁止上传数据库、原聊天/图片/候选正文、运行日志/证据、备份、凭证、本机配置/宿主绑定、原ZIP、旧.git、node_modules/.venv及排除的MRS/MPH实现。第三方依赖采用官方锁定安装，不凭项目Apache许可重新分发他人代码。

English: publish only a reviewed clean scope. Preserve earlier releases and private history, verify manifest and runtime identity, create a new package/hash, and download the asset to verify it. Configuration is not loading; public read-back is not a live hook; candidates are not full semantic or domain acceptance. This release includes generic learning/host/UI paths, while private100/900 trial orchestration is excluded.
