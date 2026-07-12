# ArchFlow

ArchFlow 是一个面向建筑方案与初步设计的可追溯自动化编排层，把施工/设计要求、敷地 CAD、官方法规证据、建筑语义模型、CAD 草图、SketchUp 模型脚本、标准视图和 AI 渲染提示词串成同一条流水线。

官网：[https://archflow.best](https://archflow.best) · 开发者：OHDESIGN · 小红书：@heikikun

可直接分发给 Codex 的 Plugin 位于 [`plugins/archflow-studio`](plugins/archflow-studio)，核心 Skill 位于其 `skills/archflow-studio` 目录。它已经合并 CAD 连接、SketchUp MCP 部署、建筑生成管线、工作站配置和法规证据归档，不要求用户预先安装三套分散 Skill。

当前版本的核心原则是：`building_model.json` 是唯一事实源；AI 负责提取、编排和提出草案，确定性脚本负责校验与生成，专业人员负责法规、结构、消防、无障碍和施工文件的最终确认。

## 当前可运行范围

- 检查内置 ArchFlow CAD Bridge、SketchUp Bridge 与建筑生成管线是否就绪。
- 校验可移植的 `archflow.project.json` 项目包。
- 从要求文本生成待复核的 `parsed_requirements.yaml`。
- 从 `building_model.json` 生成不可变运行目录：校验报告、指标、语义 DXF、SketchUp Ruby、标准视图提示词和人工审查报告。
- 默认不修改源 CAD，不执行 SketchUp 建模，不声称法规合规或施工图有效。

## 快速开始

无需安装即可从仓库运行：

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m archflow doctor --json
python -m archflow check examples/detached-house/archflow.project.json
python -m archflow run examples/detached-house/archflow.project.json --stage build --plan
python -m archflow run examples/detached-house/archflow.project.json --stage build
python -m archflow status examples/detached-house/archflow.project.json
```

统一 Skill 的工作站配置先执行只读计划，确认后再应用：

```powershell
powershell -ExecutionPolicy Bypass -File plugins\archflow-studio\skills\archflow-studio\scripts\setup_workstation.ps1
powershell -ExecutionPolicy Bypass -File plugins\archflow-studio\skills\archflow-studio\scripts\setup_workstation.ps1 -Apply
```

开发安装：

```powershell
python -m pip install -e .
archflow doctor
```

新建一个项目包：

```powershell
archflow init C:\projects\my-house --title "My House" --mode preliminary
```

## 三层架构

1. ArchFlow CAD Bridge：只读检查 DWG/DXF、导出 CAD 上下文，必要时在明确授权后执行 CAD 命令。
2. ArchFlow Design Core：维护语义模型契约，执行几何/指标校验，生成 DXF、Ruby、视图和报告。
3. ArchFlow Orchestrator：管理项目包、输入指纹、运行记录、审批门和端到端编排。

详细设计见 [docs/architecture.md](docs/architecture.md)，阶段计划见 [docs/roadmap.md](docs/roadmap.md)。

Plugin 与安装包发布流程见 [docs/distribution.md](docs/distribution.md)。构建当前 Developer Preview：

```powershell
powershell -ExecutionPolicy Bypass -File installer\windows\build_release.ps1
```

解压 Developer Preview 后先查看计划，再安装：

```powershell
powershell -ExecutionPolicy Bypass -File .\ArchFlow.Setup.ps1 -Action Plan
powershell -ExecutionPolicy Bypass -File .\ArchFlow.Setup.ps1 -Action Install
```

只有在明确希望安装器同时配置 CAD 与 SketchUp 时才增加 `-ConfigureApplications`。

## 安全与责任边界

所有输出均应标记为 `concept`、`preliminary` 或 `construction_assistance`。任何未绑定到官方来源、版本和条款的法规数值都只能显示为 `UNVERIFIED`。SketchUp Ruby 的生成不等于执行；执行必须由用户明确发起，并优先在空白或副本模型中进行。

## License

Apache-2.0，见 [LICENSE](LICENSE)。第三方组件及发布限制见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
