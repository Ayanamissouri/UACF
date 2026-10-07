# 安装、停止、卸载与隔离恢复

ROOT/repo是审查后的源码目录；ROOT/data是用户自己的新authority。CPython3.11 x64：官方 https://www.python.org/downloads/windows/ 。依赖索引 https://pypi.org/simple ，锁定requirements.lock并require-hashes，无vendor轮子。若安装失败，保留数据并记录失败，不替换实时库。

安装见README。空库不导入私人来源；没有DSH/DeepSeek或旧账仍可创建Task和查询0来源。默认前台8766，独立验证使用另一个端口且不改实时配置。前台配对为same-origin cookie，凭证不存URL/localStorage。未经授权不启用宿主全局hook或自动启动。

停止：`powershell -File ROOT/repo/ops/manage.ps1 -Action stop -Root ROOT`。只停止拥有的服务进程。普通源码安装的卸载即停止使用，保留repo/data/backups与凭证；无需删除数据库。若登记过部署指针，先停服务，再运行 `python ops/deploy.py --root ROOT uninstall --expected ID`；仅移出匹配部署指针，保留数据和旧代码。宿主配置仅按选定且after_hash匹配的注册备份执行uninstall-batch3.py；后续用户改动不覆盖。当前候选未安装全局宿主配置或登录自启动。

备份：`python -m uacf --root ROOT backup create --path NEW_BACKUP`，再verify。隔离恢复：`python -m uacf --root ROOT restore --backup NEW_BACKUP --into NEW_ISOLATED_ROOT`。恢复生成隔离authority，保持暂停/宿主映射需重新确认，不自动重放模型/工具动作；只在隔离目录doctor和检查。严禁把旧快照覆盖实时库。备份含私人资产及本机配置，永不放公开包；隔离恢复生成新凭证，不复制旧auth.json。

MCP模板在adapters/templates/ecosystem；只合入审查后的named entry，路径和宿主作用域凭证在本机设置。DSH cordis根路径为明确占位符，使用前替换为授权根；不替换用户现有全局配置。五工具的声明验证不代表模型实际调用或自动回调成功。

DeepSeek可选路线读取显式DEEPSEEK_API_KEY环境变量；默认不启动。必须有当前允许Provider的Task/冻结修订、账户预算与实时价格/能力验收；未知/reserved/dispatched/response_known先对账，复用已知成功结果。当前付费路线未在候选新环境付费测试，保持partial。

服务使用独占监听，启动请求不等于ready。停止后Windows的连接等待态可能暂时阻止重新绑定，应等待自然释放并核对/health的authority、PID及加载身份；不启用端口复用或SO_LINGER绕过保护。参考[Microsoft SO_EXCLUSIVEADDRUSE](https://learn.microsoft.com/en-us/windows/win32/winsock/so-exclusiveaddruse)。浏览器会话cookie按端口隔离，退出一个前台不退出另一端口。
