# Troubleshooting

## API Key 未配置

现象：Today 生成按钮不可用，或运行失败显示 `missing_api_key`。

处理：

1. 打开 Settings。
2. 填写 API Key 和 Model。
3. 点击 `测试连接`。
4. 保存配置后重新生成。

## AI Provider 连接失败

现象：Test Connection 失败，或运行错误为 `api_connection_failed` / `model_generation_failed`。

处理：

- 检查 API Key 是否有效。
- 检查 Base URL 是否与 provider 兼容。
- 检查 Model 名称是否存在。
- 如果公司网络需要代理，在 Settings > Network 中配置代理。

## 代理错误

现象：日志中出现 `127.0.0.1:7890`、`proxy`、`tunnel` 或连接拒绝。

处理：

- 如果不需要代理，将 Proxy mode 改为 `不使用代理`。
- 如果需要代理，确认本地代理程序正在运行。
- 更新 HTTP / HTTPS proxy 地址。

PowerShell 临时清理代理环境变量：

```powershell
Remove-Item Env:http_proxy, Env:https_proxy, Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:ALL_PROXY, Env:all_proxy -ErrorAction SilentlyContinue
```

## 没有抓取到文章

现象：`no_articles_fetched` 或 `No articles found within last N hours`。

处理：

- 将时间范围从 `24h` 调大到 `48h` 或 `7d`。
- 检查 Sources 中是否禁用了大部分 source。
- 查看失败源和代理设置。
- 稍后重试。

## 部分信息源失败

现象：Today 显示 source warning，但报告成功生成。

说明：这是可恢复状态。SignalForge Daily 会使用成功读取的信息源生成日报。

处理：

- 打开 Sources 页面查看失败源。
- 打开运行日志查看具体错误。
- 对长期失败的源执行禁用或更新 URL。

## 报告文件找不到

现象：Reports 中报告无法打开，或 Markdown preview 报错。

处理：

- 确认 workspace 和 outputPath 没有被移动。
- 打开 Settings 查看 Workspace / Output folder。
- 如果手动删除了报告文件，可以从 Reports 中移除对应 run。

## 通知权限未开启

现象：自动生成成功或失败后没有系统通知。

处理：

- 打开 Settings > Automation。
- 点击 `测试通知`。
- 在系统设置中允许 SignalForge Daily 发送通知。

## 自动生成没有触发

处理：

- 确认 Settings > Automation 中已开启自动生成。
- 确认运行时间已经到达。
- 确认 App 正在运行；v0.4 不包含 OS login-start 后台启动。
- 如果 `今天已生成则跳过` 已开启，同一天已有成功日报时会跳过。
- 查看 Settings > About 的诊断信息和 logs folder。

## Windows SmartScreen 提示

现象：安装包提示未知发布者或 SmartScreen。

原因：v0.4 本地构建默认未签名。

处理：

- 只安装来自可信 Release 页面或自己构建的安装包。
- 发布正式版本前应使用代码签名证书签名 installer。

## 如何打开 logs folder

方式一：Settings > About > `打开 logs folder`。

方式二：在 workspace 中打开：

```text
<workspace>\logs\
```

方式三：运行失败卡片中点击 `Open Logs` / `查看运行日志`。
