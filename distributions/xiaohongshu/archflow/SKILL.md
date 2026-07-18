---
name: archflow
description: 在 Windows 本地检查和配置 CAD/SketchUp 工作环境，读取 DWG/DXF 上下文，基于可追溯的官方法规与项目要求建立建筑语义模型，校验几何与面积指标，生成新的 DXF 和可审查的 SketchUp 模型，自动捕获标准视角或用户当前视角，并按用户选择的风格生成保持几何的建筑概念效果图和不可覆盖的审查记录。适用于住宅及建筑概念设计、方案深化、施工辅助、CAD 到 SketchUp 建模、设计比较，以及用户提到渲染、效果图、概念图、出图或 visualization 时；不得把结果称为报批、法律、结构或最终施工结论。
---

# ArchFlow Studio 小红书版

把本目录当作独立、完整的工作流包使用。优先执行只读检查；仅在用户明确要求并确认目标路径后，执行会写入 CAD、SketchUp 或用户目录的步骤。

官方网站：https://archflow.best

当前为 OHDESIGN（@heikikun）发布的 Apache-2.0 开发者预览版。所有建筑、法规与施工输出必须由专业人员复核。

## 先确认运行边界

1. 阅读 [permissions-and-security.md](references/permissions-and-security.md)，向用户说明本次所需权限和实际写入位置。
2. 确认运行在 Windows，并可调用 Python 3 和 PowerShell 5.1 或更高版本。
3. 仅在相关任务需要时要求用户安装并打开 CAD 或 SketchUp；纯法规整理、语义建模和文件生成不要求连接这些应用。
4. 不收集账号、Cookie 或平台凭据，不发送遥测，不静默安装软件，不自动修改 Agent/MCP 全局配置。

## 不可违反的规则

- 将输出标为 `concept`、`preliminary` 或 `construction_assistance`。
- 不得声称结果已经报批、完全合法、结构批准或可直接施工。
- 保持源 DWG/DXF 只读；把生成文件写入用户指定的项目输出目录。
- 将加载 CAD 命令、安装 SketchUp 扩展、执行 Ruby、删除或覆盖模型实体视为变更。先展示计划、目标路径和回滚方式，再等待用户明确同意。
- 仅接受带有管辖地、发布机关、标题、版本/生效日、网址或用户文件、准确条款/页码、获取时间和内容哈希的法规依据。信息不全时标记 `UNVERIFIED`。
- 不编造结构、防火、疏散、无障碍、土壤、基础或机电要求。
- 架构或几何校验失败时停止后续生成；警告只有写入审查报告后才可继续。

## 按请求选择路线

1. **首次配置或修复**：阅读 [workstation-setup.md](references/workstation-setup.md)，先运行 `scripts/setup_workstation.ps1` 的只读计划。只有用户要求配置且目标无误时才加 `-Apply`。
2. **CAD 检查**：阅读 [cad-com.md](references/cad-com.md) 和 [cad-sketchup.md](references/cad-sketchup.md)，先运行 `scripts/cad-cli.ps1 diagnose`，再只读导出活动图纸上下文。
3. **法规或规划研究**：阅读 [legal-research.md](references/legal-research.md)，先确定项目地址、管辖地和设计日期，只使用官方或用户提供的来源，并通过 `scripts/legal_evidence.py` 归档证据。
4. **语义设计与生成**：阅读 [input-and-safety.md](references/input-and-safety.md) 和 [semantic-model.md](references/semantic-model.md)，建立并验证 `building_model.json`，再生成成果。
5. **SketchUp 连接与执行**：阅读 [deployment.md](references/deployment.md) 和 [modeling.md](references/modeling.md)。使用随包提供的 `scripts/archflow_mcp_server.py` 与 ArchFlow Bridge；先做只读验证，再检查 Ruby 和 SHA-256，最后在空白或副本模型中经用户确认后执行。
6. **视图与渲染**：阅读 [render-views.md](references/render-views.md)。SketchUp 建模成功后或用户提到渲染、效果图、概念图、出图时自动进入此路线。Bridge 可用时通过 `sketchup_capture_view` 捕获标准场景或用户当前视角，不要求用户另行截图上传。

## 端到端流程

1. 运行工作站检查并输出配置计划。
2. 盘点场地 CAD、需求、法规文件、管辖地、版本、单位、原点、标高和北向。
3. 研究适用的国家、地方、地区规划、防火、无障碍、节能、景观及协议来源。
4. 建立法规证据包，分开记录已核实约束和待专业人员解释的内容。
5. 只读导出 CAD 上下文；边界或道路含义不明确时，请用户指定权威对象。
6. 创建 `archflow.project.json`、`requirements.yaml` 和唯一语义源 `building_model.json`。
7. 验证 ID、多边形、洞口宿主、楼层体积、面积、建筑覆盖率/容积率/高度/退界、来源和人工复核门槛。
8. 在新的不可覆盖运行目录中生成语义 DXF、SketchUp Ruby、指标、报告、渲染提示、哈希和日志。
9. 仅在明确要求下，分批应用 CAD/SketchUp 变更，并回读实体数量、标签、组、场景及导出文件验证结果。
10. 比较警告和设计目标，修改语义模型并创建新运行，不覆盖历史证据。
11. SketchUp 建模完成后提供视角选择，只收集缺失的风格偏好，捕获视图、生成可追溯渲染任务，并在用户完成选择后立即调用可用的图像编辑工具。

## 自动渲染交接

1. 建模完成后或识别到任何渲染意图时自动触发，不要求单独截图。
2. 用户没有指定视角时，优先用客户端结构化选择按钮；不支持按钮时用一行编号选项：`当前 SketchUp 视角`、`Front`、`Right`、`Top`、`Axon`、`全部标准视角`。选择当前视角前提醒用户先完成旋转、平移和缩放。
3. 视角已给出时不重复提问，通过 `sketchup_capture_view` 把 PNG 写入当前运行的 `render_inputs/`。
4. 风格缺失时只问一次。运行 `python scripts/render_workflow.py list-styles`，显示简短名称和一句说明；接受目录别名或自由描述的自定义风格。
5. 用户选择视角和风格即视为生成指示，不再二次确认。运行 `render_workflow.py prepare` 写入 `render_jobs/<view>.json`。
6. 当前环境提供图像生成/编辑工具时，立即以捕获 PNG 为参考图执行图像编辑，优先高输入保真；已有视图时不得改用纯文字生图。
7. 环境没有图像工具时，仅完成渲染任务和提示词，不得谎称已经出图；用一句话说明缺少 Provider。
8. 对照源图检查相机、裁切、建筑轮廓、层数、屋顶、洞口、退界和相邻几何，并将结果标为 `concept visualization`。

## 常用命令

先做只读环境检查：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_workstation.ps1
python scripts/archflow_cli.py doctor --json
```

创建并运行项目：

```powershell
python scripts/archflow_cli.py init C:\projects\my-house --title "My House" --mode preliminary --core-skill .
python scripts/archflow_cli.py run C:\projects\my-house\archflow.project.json --stage build --core-skill .
```

只读检查和导出 CAD：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/cad-cli.ps1 diagnose
powershell -ExecutionPolicy Bypass -File scripts/cad-cli.ps1 export -OutputPath .\cad-context.json
```

只有用户确认配置时执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_workstation.ps1 -Apply
```

归档官方法规证据和比较设计版本：

```powershell
python scripts/legal_evidence.py init --jurisdiction "Japan/Tokyo/Example City" --effective-date 2026-07-12 --output-dir legal
python scripts/legal_evidence.py verify --bundle legal
python scripts/design_optimizer.py --baseline-run outputs\runs\BASE --candidate-run outputs\runs\CANDIDATE --objectives optimization_objectives.json --output optimization_report.json
```

列出风格并准备渲染任务：

```powershell
python scripts/render_workflow.py list-styles
python scripts/render_workflow.py prepare --source-image outputs\runs\RUN\render_inputs\current.png --view current --style golden-hour --model model\building_model.json --render-manifest outputs\runs\RUN\render_prompts\manifest.json --output outputs\runs\RUN\render_jobs\current.json
```

## 输出约定

完整运行应包含 `parsed_requirements.yaml`、`building_model.json` 或其输入哈希、`metrics.json`、`validation_report.json`、`review_report.md`、`semantic_plans.dxf`、`build_model.rb`、`render_prompts/`、`run.json` 及标准输出/错误日志。用户要求渲染时还应包含 `render_inputs/` 源 PNG、`render_jobs/` 任务清单，以及生成的概念图或明确的 Provider 不可用记录。法规研究还应包含 `legal_evidence.json` 和归档的来源文件。

重新发布本 Skill 前，阅读 [third-party-notices.md](references/third-party-notices.md)，运行 `python scripts/validate_skill_package.py .`。上传 ZIP 时，确保 `SKILL.md` 位于 ZIP 根目录。
