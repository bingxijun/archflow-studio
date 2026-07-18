---
title: ArchFlow Studio Developer Preview 安装与使用指南
description: 在 Windows 上安装 ArchFlow Studio，并连接 Codex、CAD 与 SketchUp 的完整使用说明。
---

# ArchFlow Studio Developer Preview 安装与使用指南

ArchFlow Studio 是面向建筑方案与初步设计的可追溯自动化工作流。它把施工或设计要求、敷地 CAD、官方法规证据、建筑语义模型、CAD 草图、SketchUp 模型和基于所选视角的概念渲染连接到同一套 Codex 工作流中。

> ArchFlow Studio Developer Preview  
> 开发者：OHDESIGN  
> 小红书：@heikikun
> 官网：https://archflow.best
>
> 当前为未签名开发者预览版。  
> 支持安装、检测和配置，但不同 CAD/SketchUp 版本的兼容性可能存在差异。  
> 所有建筑、法规及施工输出必须由专业人员复核。

## 下载

普通用户只需要下载一个 Windows ZIP，不需要另外下载或安装独立 RBZ。

**当前版本**

```text
0.2.0-dev.1+codex.20260712222909
```

**下载入口**

百度网盘下载：**发布前请在这里填入分享链接和提取码**

**SHA-256**

```text
01AE14A526E5EF8FB146D8BCBDF4206CCA694061E00326E84C2C51B073A47A0F
```

安装包已经包含 Codex Plugin、ArchFlow Skill、CAD Bridge、SketchUp Bridge RBZ、MCP 服务、检测脚本、安装器、许可证和校验文件。

`ArchFlow Bridge unsigned RBZ` 是 OHDESIGN 用于 SketchUp 官方签名流程的开发文件，普通用户不需要下载。

## 安装前准备

请确认电脑满足以下条件：

- Windows 桌面环境与 PowerShell 5.1 或更高版本。
- 已安装 Codex 桌面应用。
- 已安装 Python 3.11 或更高版本，并且在 PowerShell 中可以运行 `python --version`。
- 如果需要 CAD 功能，请先安装并启动用户自己的 CAD 软件。
- 如果需要 SketchUp 功能，请先安装并至少启动一次 SketchUp，让软件创建用户插件目录。

当前 Developer Preview 不包含 Python、CAD、SketchUp 或其他商业软件本体，也不包含这些软件的许可证。

## 完整安装：Codex + CAD + SketchUp

### 1. 解压安装包

下载完成后，将 ZIP 完整解压到普通文件夹。不要直接在压缩包预览窗口中运行安装脚本。

建议路径示例：

```text
C:\ArchFlow-Studio
```

### 2. 打开 PowerShell

进入解压后的文件夹。在文件夹空白处按住 Shift 并单击鼠标右键，选择“在此处打开 PowerShell 窗口”或“在终端中打开”。

### 3. 先执行只读检查

```powershell
powershell -ExecutionPolicy Bypass -File .\ArchFlow.Setup.ps1 -Action Plan -ConfigureApplications
```

Plan 模式只显示安装位置、软件检测结果和即将执行的操作，不会修改文件。

请检查：

- Codex Plugin 安装位置是否正确。
- 是否检测到 Python。
- 是否检测到需要使用的 CAD 软件。
- 是否找到正确的 SketchUp Plugins 文件夹。
- 本地端口 `127.0.0.1:9877` 是否可用。

### 4. 执行完整安装

确认 Plan 没有明显异常后运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\ArchFlow.Setup.ps1 -Action Install -ConfigureApplications
```

安装器将：

- 把 ArchFlow Studio Plugin 安装到当前 Windows 用户目录。
- 把 Plugin 注册到当前用户的 Codex Personal Marketplace。
- 检测当前可用的 CAD 自动化接口。
- 备份已有的同名 SketchUp Bridge 文件。
- 将内置 ArchFlow SketchUp Bridge 部署到检测到的 SketchUp 用户插件目录。
- 创建仅供本机桥接使用的随机配对令牌。
- 在当前用户的 `%LOCALAPPDATA%\ArchFlow\PREVIEW_NOTICE.txt` 保存 Developer Preview 声明。

工作站配置不会修改 CAD 源图，也不会自动修改当前 SketchUp 模型中的几何体。

### 5. 重启软件

安装完成后：

1. 完全关闭并重新启动 Codex。
2. 在 Codex 中新建一个任务，使新版 Plugin 和 Skill 被重新加载。
3. 完全关闭并重新启动 SketchUp。
4. 第一次加载当前预览版本时，SketchUp 会为当前用户显示一次 Developer Preview 提示。
5. 建议先打开空白 SketchUp 模型进行连接测试。

## 只安装 Codex Plugin

如果暂时不希望安装器配置 SketchUp，只运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\ArchFlow.Setup.ps1 -Action Install
```

此模式会安装 Codex Plugin，但不会主动部署 SketchUp Bridge。CAD 和 SketchUp 完整连接可以稍后通过 Repair 补充：

```powershell
powershell -ExecutionPolicy Bypass -File .\ArchFlow.Setup.ps1 -Action Repair -ConfigureApplications
```

## 验证安装

### 在 Codex 中验证

重启 Codex 并新建任务后，可以输入：

```text
检查我的 ArchFlow、CAD 和 SketchUp 连接状态，只进行只读检测。
```

也可以输入：

```text
检查当前 SketchUp Bridge 状态，并读取当前空白模型的场景信息。
```

正常情况下，Codex 应能识别 ArchFlow Studio Plugin，并报告 SketchUp Bridge 的本地连接状态。

### 在 SketchUp 中验证

打开 SketchUp 后检查：

1. 打开“扩展程序管理器”。
2. 确认列表中存在 `ArchFlow Bridge`。
3. 打开“扩展程序”菜单，确认存在 `ArchFlow Bridge` 子菜单。
4. 如有需要，点击 `Start Local Bridge`。

当前版本尚未取得 SketchUp 官方数字签名。如果 SketchUp 阻止加载，请在扩展程序管理器的加载策略中选择允许用户批准未识别扩展的模式，然后重启 SketchUp。不要在不信任安装包来源的电脑上降低加载限制。

SketchUp 官方加载策略说明：  
https://help.sketchup.com/en/extensions-loading-policy

### 在 CAD 中验证

启动需要使用的 CAD 软件并打开源图的副本，然后在 Codex 中输入：

```text
只读检查当前 CAD 图纸，汇总图层、单位、范围和基础对象数量，不要修改图纸。
```

ArchFlow 默认通过用户已安装 CAD 的自动化接口进行只读检查，不会永久修改 CAD 安装。只有需要 CAD 内部辅助命令时，才需要用户明确同意加载附带的 AutoLISP Bridge。

## 基本使用示例

### 读取项目要求

```text
阅读这个项目的施工和设计要求，整理为待人工复核的结构化需求，不要直接声称符合法规。
```

### 检查敷地 CAD

```text
只读检查敷地 CAD，识别边界、道路、标高、现有建筑和主要图层，并列出不确定项。
```

### 查询法规证据

```text
根据项目所在地查找官方法规来源，记录法规名称、发布机构、生效日期、链接和待确认条款。
```

法规查询应优先使用政府或主管机关的官方来源。任何没有绑定官方来源、版本和条款的数值都应标记为 `UNVERIFIED`。

### 生成可复核方案

```text
根据已确认的需求和敷地条件生成 preliminary 级别的建筑语义模型、CAD 草图和 SketchUp 模型脚本，并输出人工审查清单。
```

### 建模完成后生成概念效果图

建模成功后，ArchFlow 会进入渲染交接。用户可以选择 `Front`、`Right`、`Top`、`Axon`、全部标准视图，或先在 SketchUp 中旋转到心仪角度后选择“当前视角”。Bridge 会自动捕获 PNG，不要求用户另外截图。

如果用户尚未指定风格，ArchFlow 只询问一次风格。内置选项包括写实日景、金色黄昏、蓝调暮色、夜景、阴天极简、日式自然极简、电影感、水彩、铅笔草图、白模、等距分析、材质研究和室内柔光，也接受自由描述。

```text
使用 $archflow-studio，把我当前 SketchUp 视角渲染成金色黄昏的写实建筑效果图，严格保持相机、轮廓、层数、屋顶和门窗位置。
```

当前 Codex 环境提供图像生成/编辑工具时，用户完成视角和风格选择后会直接生成；环境未提供图像工具时，只生成可追溯任务和提示词并明确说明原因。所有结果均为 `concept visualization`。

### 比较方案

```text
比较基准方案和候选方案的面积、层数、退界、主要空间关系和验证警告，不要覆盖原方案。
```

## 文件和数据安全

- ArchFlow SketchUp Bridge 只监听本机地址 `127.0.0.1:9877`。
- Bridge 使用当前 Windows 用户专属的随机配对令牌。
- 不要把 `%LOCALAPPDATA%\ArchFlow\bridge-token` 上传到网盘、GitHub、聊天或项目资料中。
- 优先使用 CAD 图纸和 SketchUp 模型的副本进行首次测试。
- 自动生成 SketchUp Ruby 不等于自动执行；执行前应由用户明确确认。
- 不要把概念方案、初步方案或 AI 输出直接作为审批文件、施工图或现场施工依据。

## 修复安装

当文件损坏、Plugin 链接失效或需要补充 CAD/SketchUp 配置时运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\ArchFlow.Setup.ps1 -Action Repair -ConfigureApplications
```

Repair 会重新安装当前版本，并在替换受管理文件前保留备份。

## 卸载

```powershell
powershell -ExecutionPolicy Bypass -File .\ArchFlow.Setup.ps1 -Action Uninstall
```

卸载器会移除当前版本的 Codex Plugin 链接、Personal Marketplace 条目、安装状态和当前用户的 Preview 声明文件。

当前 Developer Preview 为避免误删用户文件，会保留已经部署到 CAD/SketchUp 目录中的适配器及其备份。需要清理这些文件时，请先核对文件名和备份，再进行人工处理。

## 常见问题

### 用户是否需要单独下载 RBZ？

不需要。Windows ZIP 已包含 ArchFlow SketchUp Bridge RBZ。独立的 unsigned RBZ 只供 OHDESIGN 进行 SketchUp 官方签名，不属于普通用户下载内容。

### 为什么执行安装后 Codex 没有立即看到 Plugin？

Codex 会在新任务中加载更新后的 Plugin。请完全重启 Codex，然后新建任务测试。

### 为什么没有检测到 SketchUp 插件目录？

请先启动一次 SketchUp，等待主界面加载后关闭，再重新运行 Plan。SketchUp 通常会在首次启动时创建当前用户的 Plugins 目录。

### 为什么 SketchUp 显示扩展未签名？

当前版本是未签名 Developer Preview。它还没有取得 SketchUp Extension Warehouse 的官方数字签名。请仅从 OHDESIGN 官方发布渠道获取安装包，并核对 SHA-256。

### 为什么 CAD 检测不到图纸？

请确认 CAD 已经启动并打开了图纸。建议使用图纸副本进行首次测试。不同 CAD 产品和版本的自动化接口可能存在差异。

### 为什么提示找不到 Python？

安装 Python 3.11 或更高版本，并在安装时启用“Add Python to PATH”。重新打开 PowerShell 后运行：

```powershell
python --version
```

确认命令可用后重新执行 Repair。

## 校验下载文件

在 ZIP 所在目录打开 PowerShell：

```powershell
Get-FileHash .\ArchFlow-Studio-0.2.0-dev.1+codex.20260712222909-windows.zip -Algorithm SHA256
```

结果应为：

```text
01AE14A526E5EF8FB146D8BCBDF4206CCA694061E00326E84C2C51B073A47A0F
```

如果哈希不一致，请不要运行安装脚本，并重新从 OHDESIGN 官方渠道下载。

## 责任边界

ArchFlow Studio 当前用于建筑方案、初步设计、资料整理和施工辅助，不代替建筑师、结构工程师、消防顾问、设备工程师、行政机关或其他具备法定资格的专业人员。

所有自动生成结果都应明确标记为以下阶段之一：

- `concept`
- `preliminary`
- `construction_assistance`

所有建筑、法规及施工输出必须由专业人员复核后才能进入后续流程。

## 联系方式

开发者：**OHDESIGN**  
项目：**ArchFlow Studio**  
小红书：**@heikikun**  
官网：**https://archflow.best**
