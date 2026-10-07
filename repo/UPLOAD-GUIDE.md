# GitHub上传与更新 / Publishing and updating

项目所有者已选择Apache-2.0。当前已获得“确认自己的GitHub账号登录后尝试合规上传”的条件授权；实际Firefox页面捕获失败，尚未确认账号和目标仓库，当前未上传。本地候选包含干净源码、双语设计和使用说明、启动/宿主配置入口、三个抽象指导模块与合成测试。

先核对PUBLIC-MANIFEST.json逐文件范围、EXCLUSIONS.json、NOTICE、THIRD_PARTY、SBOM、LICENSE-GAPS和冻结包hash。代码或文档改变后须新冻结与相关复测。不得上传私人数据库、聊天、图片、候选正文、凭证、日志、备份、原ZIP、机器配置、旧.git或排除的MRS/MPH代码。公开模块只保留通用原则、条件、合成例子及限制；本地来源链接不进入公开包。

在独立干净导出目录建立首次公开Git历史，逐blob复核公开历史；不直接push旧私有仓库。依赖从官方渠道按锁重建，不打包未经再分发审查的轮子或第三方实现。实际宿主已配置不等于已加载；公开回读不等于live hook；没有全900语义验收或全100发布的声明。

Publish only this reviewed clean scope to the verified owner repository. Create fresh public history, inspect every public blob, and retain private provenance locally. Never push the old private history. Modules remain advisory and must be reviewed after import. A new hash and relevant validation are required after changes. Nothing has been uploaded in this preparation.
