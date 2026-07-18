# 权限与安全说明

## 默认只读行为

- 读取用户明确提供的项目文件、CAD 活动图纸元数据、法规文件和 Skill 自带模板。
- 检查 Windows 注册表中的 SketchUp 安装信息、用户目录中的 SketchUp 插件目录、Python/PowerShell 可用性和本机端口 `127.0.0.1:9877`。
- 不读取浏览器 Cookie、账号口令、通讯录或与项目无关的个人文件。

## 需要用户确认的写入

只有用户明确要求并确认目标路径后，才执行以下操作：

- 在用户指定的项目输出目录创建 DXF、JSON、YAML、Ruby、报告、渲染提示、日志和哈希记录。
- 使用 `-Apply` 将 `archflow_bridge.rb` 和 `archflow_bridge/` 写入选定的 SketchUp `Plugins` 目录；覆盖同名旧文件前创建带时间戳的备份。
- 在 `%LOCALAPPDATA%\ArchFlow\bridge-token` 创建本机随机配对令牌。不得在回复、日志或报告中输出令牌内容。
- 把 `assets/codex_cad_bridge.lsp.txt` 复制为 `%LOCALAPPDATA%\ArchFlow\generated\codex_cad_bridge.lsp` 后加载到用户打开的 CAD，或在空白/副本 SketchUp 模型中执行已展示、已校验哈希的 ArchFlow Ruby。
- 删除 SketchUp 实体前必须单独说明实体 ID 和影响，并获得明确同意。

## 网络与进程

- `scripts/legal_evidence.py fetch` 仅在用户要求法规研究时访问用户确认的 HTTPS 官方网址，并把响应保存到项目证据目录。
- SketchUp Bridge 只监听 `127.0.0.1:9877`，使用本机令牌；不暴露到局域网或公网，不发送遥测。
- Skill 可启动 `python` 和 `powershell` 子进程，并通过 Windows COM 与已打开的 CAD 交互。
- 不克隆仓库、不自动安装依赖、不执行编码/混淆命令、不下载并执行远程代码、不自动修改 Agent 或 MCP 的全局配置。

## 独立部署说明

- 核心语义建模、校验、DXF/Ruby/报告生成可直接通过 `scripts/archflow_cli.py` 运行。
- 交互式 SketchUp 工具需要运行时支持 stdio MCP。Skill 自带透明源码 `scripts/archflow_mcp_server.py`，配置示例位于 `assets/mcp/archflow-sketchup.json`；让用户按其 Agent 宿主的方式手动注册，不要静默写入全局配置。
- SketchUp 扩展的透明文本源码位于 `assets/sketchup-extension/*.rb.txt`。应用安装时在 `%TEMP%\ArchFlow\archflow_bridge.rbz` 可复现构建两文件 ZIP，并通过 `assets/integration-lock.json` 校验 SHA-256；发布包不携带二进制 RBZ。

## 专业复核

所有规划、法律、结构、防火、无障碍、机电、测量、岩土、造价与施工结论必须由相应的持证专业人员或主管机关复核。Skill 输出只用于概念、方案或施工辅助阶段。
