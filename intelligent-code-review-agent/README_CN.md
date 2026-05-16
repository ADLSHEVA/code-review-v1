# 智能代码审查 Agent — 中文使用指南

基于 AI 的代码审查工具，**深度支持工业 PLC/ICS 代码审查**。支持 7 大 PLC 厂商解析、3 种图形语言转换、30+ 安全/可靠性规则、控制流分析、硬件配置校验，以及 LLM 微调数据生成。

---

## 目录

- [环境准备](#环境准备)
- [快速开始：三步审查你的代码](#快速开始三步审查你的代码)
- [详细使用教程](#详细使用教程)
  - [场景1：审查 Git 提交](#场景1审查-git-提交)
  - [场景2：审查两个分支差异](#场景2审查两个分支差异)
  - [场景3：审查 PLC 项目](#场景3审查-plc-项目)
  - [场景4：生成 LLM 微调数据](#场景4生成-llm-微调数据)
- [网页版 GUI](#网页版-gui)
  - [仪表盘](#仪表盘)
  - [新建扫描](#新建扫描)
  - [文件扫描（拖拽上传）](#文件扫描拖拽上传)
  - [报告查看器](#报告查看器)
  - [报告对比](#报告对比)
  - [知识库管理](#知识库管理)
  - [系统设置](#系统设置)
- [部署指南](#部署指南)
  - [后端 (FastAPI)](#后端-fastapi)
  - [前端 (Vue 3)](#前端-vue-3)
  - [生产环境构建](#生产环境构建)
- [模型配置](#模型配置)
  - [切换模型](#切换模型)
  - [自定义 API 端点（Mimo 等）](#自定义-api-端点mimo-等)
  - [支持的模型 ID](#支持的模型-id)
- [PLC 厂商支持详解](#plc-厂商支持详解)
- [图形语言转换](#图形语言转换)
- [规则检查器详解](#规则检查器详解)
- [控制流图分析](#控制流图分析)
- [硬件配置验证](#硬件配置验证)
- [LLM 微调数据管道](#llm-微调数据管道)
- [外部工具集成](#外部工具集成)
- [支持的编程语言（28种）](#支持的编程语言28种)
- [配置参数说明](#配置参数说明)
- [项目结构](#项目结构)
- [运行测试](#运行测试)

---

## 环境准备

### 1. Python 环境

需要 Python 3.10+，推荐 3.12：

```powershell
# 检查 Python 版本
python --version
# 或
py --version
```

### 2. 安装依赖

```powershell
# 进入项目目录
cd "D:\AI_Models\agent\xiaomi version\intelligent-code-review-agent"

# 方式1：pip 安装（推荐）
pip install -e .

# 方式2：手动安装核心依赖
pip install langchain-anthropic langchain-core pydantic-settings chromadb sentence-transformers tenacity rich gitpython
```

### 3. 配置 API Key

在项目根目录创建 `.env` 文件：

```powershell
# 创建 .env 文件
@"
ANTHROPIC_API_KEY=你的API密钥
CLAUDE_MODEL=claude-sonnet-4-20250514
"@ | Out-File -FilePath ".env" -Encoding utf8
```

**支持的 API 端点：**

| 端点 | 配置示例 |
|------|----------|
| Anthropic 官方 | `ANTHROPIC_API_KEY=sk-ant-...` |
| 自定义兼容端点 (如 Mimo) | `ANTHROPIC_BASE_URL=https://your-endpoint.com/v1` |
| 禁用 thinking 模式 | `DISABLE_THINKING=true` |

---

## 快速开始：三步审查你的代码

假设你有一个 PLC 项目在 `D:\MyPLCProject`，想审查最新一次提交的代码：

### 第1步：进入项目目录

```powershell
cd "D:\AI_Models\agent\xiaomi version\intelligent-code-review-agent"
```

### 第2步：运行审查（审查 HEAD 提交）

```powershell
python -m src.main "D:\MyPLCProject" --commit HEAD
```

### 第3步：查看结果

审查结果会直接打印到终端，包含：
- 发现的问题数量和严重程度分布
- 每个问题的文件、行号、描述和修复建议

**输出示例：**

```
Found 5 changed files, +120 -30 lines
Running AI review...

Code Review Report
==================

Found 8 issue(s): 2 critical, 3 errors, 2 warnings, 1 info.

## D:\MyPLCProject\MotorControl.st

### [CRITICAL] PLC-006: Division without zero check
Line 45: Result := Speed / Divisor;  // 除数未检查是否为零
Suggestion: 添加 IF ABS(Divisor) > 0.001 THEN ... END_IF;

### [ERROR] PLC-009: Missing emergency stop handling
Line 12: Motor := StartButton AND NOT StopButton;  // 未检查急停
Suggestion: 添加 EStop 信号检查

### [WARNING] PLC-003: Magic number
Line 23: IF Speed > 1500 THEN  // 1500 是什么含义？
Suggestion: 定义常量 VAR CONSTANT MAX_SPEED : INT := 1500;
```

---

## 详细使用教程

### 场景1：审查 Git 提交

```powershell
# 审查最新一次提交
python -m src.main "D:\MyPLCProject" --commit HEAD

# 审查指定 commit
python -m src.main "D:\MyPLCProject" --commit abc1234

# 输出为 JSON 格式
python -m src.main "D:\MyPLCProject" --commit HEAD --format json

# 保存到文件
python -m src.main "D:\MyPLCProject" --commit HEAD -o review_result.md

# 指定模型
python -m src.main "D:\MyPLCProject" --commit HEAD --model claude-opus-4-7
```

### 场景2：审查两个分支差异

```powershell
# 比较 main 分支和 feature 分支
python -m src.main "D:\MyPLCProject" --base main --head feature/new-motor

# 比较两个 tag
python -m src.main "D:\MyPLCProject" --base v1.0 --head v1.1

# 输出 JSON 到文件
python -m src.main "D:\MyPLCProject" --base main --head develop --format json -o review.json
```

### 场景3：审查 PLC 项目

PLC 项目的审查流程与普通代码完全一样，工具会自动识别 PLC 文件并执行深度分析：

```powershell
# 审查一个 TIA Portal 项目导出
python -m src.main "D:\TIA_Project" --commit HEAD

# 审查 TwinCAT 项目
python -m src.main "D:\TwinCAT_Project" --commit HEAD

# 审查 CODESYS 项目（WAGO、Schneider 等）
python -m src.main "D:\CodesysProject" --commit HEAD

# 审查 Rockwell L5X 导出
python -m src.main "D:\Studio5000_Project" --commit HEAD
```

**PLC 审查自动执行的分析：**

1. **厂商解析** — 自动检测 XML 格式（Siemens/Beckhoff/CODESYS/Rockwell/ABB/GE/Omron）
2. **图形语言转换** — LD/FBD/SFC 自动转 ST
3. **30+ 规则检查** — 模式匹配 + 结构分析 + 语义分析
4. **控制流分析** — 不可达代码、死循环、未初始化变量、死代码
5. **外部工具** — 自动检测并运行已安装的 IEC Checker、plc-lint
6. **硬件配置** — TIA Portal HWConfig XML 自动验证
7. **LLM 审查** — AI 深度语义分析

### 场景4：生成 LLM 微调数据

```powershell
# 从规则库 + 漏洞数据库生成训练数据
python -m src.plc.finetune.cli --output ./data/training.jsonl

# 从真实代码库扫描生成
python -m src.plc.finetune.cli --repo "D:\MyPLCProject" --output ./data/training.jsonl

# 导出 Alpaca 格式，自动划分训练/验证/测试集
python -m src.plc.finetune.cli --format alpaca --split --output-dir ./data/

# 导出 ShareGPT 格式
python -m src.plc.finetune.cli --format sharegpt --output ./data/sharegpt.json

# 打印数据集统计
python -m src.plc.finetune.cli --stats
```

**输出格式说明：**

| 格式 | 用途 | 文件示例 |
|------|------|----------|
| JSONL | OpenAI/Anthropic 微调 | `{"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}` |
| Alpaca | LLaMA 系列微调 | `{"instruction": "...", "input": "...", "output": "..."}` |
| ShareGPT | 多轮对话微调 | `{"conversations": [{"from": "human", ...}, {"from": "gpt", ...}]}` |

---

## 网页版 GUI

项目包含一个基于 **Vue 3 + TypeScript + Pinia** 构建的全功能网页界面，提供可视化的扫描、报告查看、知识库管理和系统配置功能。

### 启动网页界面

```powershell
# 终端 1：启动后端 API
cd "D:\intelligent-code-review-agent"
py -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# 终端 2：启动前端开发服务器
cd web
npm install
npm run dev
# 打开 http://localhost:5174
```

### 仪表盘

首页（`/`）按仓库文件夹分组显示所有历史扫描报告，每个报告卡片包含：

- **仓库路径**和扫描时间
- **问题严重程度分布**（严重 / 错误 / 警告 / 信息）彩色标签
- **审查摘要**
- 点击任意报告卡片查看完整报告

### 新建扫描

扫描页面（`/scan`）提供两种模式：

**单次提交模式** — 审查特定 commit 的变更：
- 输入仓库路径（如 `D:\MyProject`）
- 输入 commit SHA 或 `HEAD`（最新提交）
- 点击"开始扫描"

**分支差异模式** — 比较两个分支的差异：
- 输入仓库路径
- 设置基准分支（默认：`main`）和目标分支（默认：`develop`）
- 点击"开始扫描"

**RAG 知识库面板** — 右侧栏显示当前 RAG 知识库状态：
- 默认知识库文件数量（3 个内置）
- 自定义上传的知识库文件数量
- 向量搜索的总索引块数
- 管理知识库的快捷链接

**进度追踪** — 扫描过程中，实时进度条显示：
- 当前进度百分比
- 已处理文件数 / 总文件数
- 当前扫描的文件路径
- 已用时间

### 文件扫描（拖拽上传）

文件扫描页面（`/file-scan`）允许直接扫描单个代码文件，无需 git 仓库：

1. **拖拽**代码文件到上传区域，或点击浏览选择文件
2. 系统根据文件扩展名自动检测编程语言
3. 显示语言标签（已识别）或"不支持"（未识别）
4. 点击 **"扫描"** 开始漏洞分析
5. 完成后自动跳转到报告页面

支持的文件类型：全部 28 种支持的编程语言（见[支持的编程语言](#支持的编程语言28种)）。

### 报告查看器

报告页面（`/report/:id`）展示完整的审查结果：

- **摘要** — 高层发现概述
- **问题列表** — 按严重程度排序（严重 → 错误 → 警告 → 信息）
- 每个问题显示：文件路径、行范围、分类、标题、描述和修复建议
- **筛选** — 按严重程度或分类过滤
- **文件覆盖** — 已审查和已跳过的文件列表

### 报告对比

对比页面（`/compare`）允许并排比较两份扫描报告：

- 从下拉菜单选择两份报告
- 查看问题数量、严重程度分布和新增/已解决问题的差异
- 适用于跟踪提交间的代码质量改进

### 知识库管理

知识库页面（`/guidelines`）管理 RAG 知识库：

- **上传**自定义知识库文件（`.md`、`.txt`、`.rst`、`.adoc`、`.pdf`、`.docx`）
- **查看**所有已上传的知识库文件及块数
- **删除**单个知识库文件
- **重建索引** — 更改后重新索引向量存储
- 上传的知识库文件会自动分块并建立向量索引

### 系统设置

设置页面（`/settings`）显示当前配置信息：

- **模型** — 当前配置的 LLM 模型
- **API 端点** — API 基础 URL
- **支持的语言** — 完整的 28 种支持语言及其文件扩展名
- **审查参数** — 置信度阈值、最大上下文 token 数、温度参数

---

## 部署指南

### 后端 (FastAPI)

```powershell
# 安装 Python 依赖
cd "D:\intelligent-code-review-agent"
pip install -e .

# 启动 API 服务器（开发模式）
py -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# 启动 API 服务器（生产模式）
py -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

API 服务器提供的接口：
- `POST /api/scan/start` — 启动新的扫描任务
- `GET /api/scan/status/{job_id}` — 查询扫描进度
- `GET /api/scan/reports` — 列出所有报告
- `GET /api/report/{id}` — 获取特定报告
- `POST /api/file-scan/` — 上传并扫描单个文件
- `GET /api/guidelines/list` — 列出知识库文件
- `POST /api/guidelines/upload` — 上传知识库文件
- `GET /api/health` — 健康检查端点

### 前端 (Vue 3)

```powershell
cd web

# 安装依赖
npm install

# 开发服务器（支持热重载）
npm run dev
# 运行在 http://localhost:5174，/api 请求代理到后端

# 类型检查
npm run type-check

# 代码检查
npm run lint
```

### 生产环境构建

```powershell
# 构建前端
cd web
npm run build

# 构建产物在 web/dist/ 目录
# 后端会通过 StaticFiles 自动提供这些文件
# 只需启动后端即可访问 http://localhost:8000
py -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**生产环境架构：**
- FastAPI 后端从 `web/dist/` 目录提供 Vue SPA 静态文件
- 所有 `/api/*` 路由由后端处理
- 其他路由回退到 `index.html`（客户端路由）
- 无需额外的 Web 服务器（nginx 等）

---

## 模型配置

### 切换模型

编辑项目根目录的 `.env` 文件来更换 LLM 模型：

```env
# 使用 Claude Sonnet（默认，推荐用于大多数场景）
CLAUDE_MODEL=claude-sonnet-4-20250514

# 使用 Claude Opus（最高质量，较慢）
CLAUDE_MODEL=claude-opus-4-7

# 使用 Claude Haiku（最快，质量较低）
CLAUDE_MODEL=claude-haiku-4-5-20251001
```

修改 `.env` 文件后，需要重启后端服务器才能生效。

### 自定义 API 端点（Mimo 等）

使用兼容的 API 端点（如 Mimo、OpenRouter 或自建代理）：

```env
# 指向自定义端点
ANTHROPIC_BASE_URL=https://your-endpoint.com/v1
ANTHROPIC_API_KEY=your-api-key-here

# 对于不支持扩展思考的推理模型
DISABLE_THINKING=true
```

**重要说明：**
- Mimo 等推理模型需要设置 `DISABLE_THINKING=true`，因为它们不支持 Claude 的扩展思考功能
- 自定义端点必须兼容 Anthropic Messages API 格式
- `ANTHROPIC_API_KEY` 会作为 `x-api-key` 请求头发送

### 支持的模型 ID

| 模型 | ID | 适用场景 |
|------|-----|----------|
| Claude Sonnet 4 | `claude-sonnet-4-20250514` | 默认，速度与质量均衡 |
| Claude Opus 4 | `claude-opus-4-7` | 最高质量分析 |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | 最快，适合简单审查 |

也可以使用自定义端点支持的任意模型 ID。

---

## PLC 厂商支持详解

### 自动检测流程

当工具遇到 `.xml` 文件时，按以下顺序尝试解析：

```
SimaticML (西门子) → TwinCAT (倍福) → CODESYS (WAGO/Schneider等)
→ Rockwell (罗克韦尔) → ABB → GE/Fanuc → Omron → 通用解析器
```

第一个成功匹配的解析器会被使用。

### 各厂商解析能力

| 厂商 | 项目格式 | 提取内容 | 典型设备 |
|------|----------|----------|----------|
| **西门子** | TIA Portal SimaticML | SCL 代码、变量、网络、DB | S7-1200, S7-1500 |
| **倍福** | TwinCAT 3 TcPOU | ST/LD/FBD/SFC 代码、CDATA 处理 | CX 系列, AX 系列 |
| **CODESYS** | V3 项目文件 | ST/LD/FBD/SFC/IL、设备配置 | WAGO 750, Schneider M340 |
| **罗克韦尔** | Studio 5000 L5X | ST/RLL 代码、Tag 定义 | CompactLogix, ControlLogix |
| **ABB** | Automation Builder | ST 代码、CODESYS 兼容 | AC500 系列 |
| **GE/Fanuc** | Proficy Machine Edition | ST 代码、程序块 | PACSystems RX3i/RX7i |
| **欧姆龙** | Sysmac Studio .smc2 | ST 代码、ZIP 内 XML 解析 | NJ/NX/NY 系列 |

### 代码示例：手动使用解析器

```python
from src.plc import SimaticMLParser, TwincatParser, CodesysParser

# 西门子
if SimaticMLParser.is_simaticml("project.xml"):
    block = SimaticMLParser.parse_file("project.xml")
    print(f"块名: {block.name}")
    print(f"类型: {block.block_type}")  # FC, FB, OB, DB
    print(f"语言: {block.programming_language}")  # SCL, LAD, FBD
    print(f"ST代码:\n{block.source_code}")
    for var in block.variables:
        print(f"  变量: {var.name} : {var.datatype} ({var.scope})")

# 倍福
if TwincatParser.is_twincat("TcPOU.xml"):
    project = TwincatParser.parse_file("TcPOU.xml")
    for pou in project.pous:
        print(f"POU: {pou.name} ({pou.pou_type})")
        print(f"实现:\n{pou.implementation}")

# CODESYS (WAGO, Schneider, ABB AC500 等)
if CodesysParser.is_codesys("project.xml"):
    project = CodesysParser.parse_file("project.xml")
    for pou in project.all_pous:
        print(f"{pou.pou_type} {pou.name} [{pou.language}]")
```

---

## 图形语言转换

### LD (梯形图) → ST

```python
from src.plc import LadderDiagramConverter

# 检测并转换
source = open("program.st").read()
if LadderDiagramConverter.has_graphical_language(source):
    result = LadderDiagramConverter.extract_and_convert(source)
    print(result.st_code)
```

**转换规则：**

| 梯形图元素 | ST 等价物 |
|------------|-----------|
| 常开触点 `--\| \|--` | `AND variable` |
| 常闭触点 `--\|/\|--` | `AND NOT variable` |
| 线圈 `--( )--` | `variable := TRUE/FALSE;` |
| 置位线圈 `--(S)--` | `variable := TRUE;` |
| 复位线圈 `--(R)--` | `variable := FALSE;` |
| 并联分支 | `OR` 逻辑 |
| TON/TOF/TP 定时器 | 定时器 FB 调用 |
| CTU/CTD 计数器 | 计数器 FB 调用 |

### FBD (功能块图) → ST

```python
from src.plc import FBDConverter

# 从标记中提取并转换
if FBDConverter.has_fbd_marker(source):
    result = FBDConverter.extract_and_convert(source)
    print(result.st_code)
```

**转换规则：**

| FBD 块 | ST 等价物 |
|--------|-----------|
| AND, OR, XOR, NOT | 布尔运算符 |
| ADD, SUB, MUL, DIV | 算术运算符 `+`, `-`, `*`, `/` |
| GT, GE, LT, LE, EQ, NE | 比较运算符 `>`, `>=`, `<`, `<=`, `=`, `<>` |
| MOVE | 赋值 `:=` |
| SEL, MAX, MIN, LIMIT | 选择函数 |
| INT_TO_REAL 等 | 类型转换函数 |
| TON, TOF, TP | 定时器 FB 调用 |
| CTU, CTD, CTUD | 计数器 FB 调用 |

**工作原理：** 解析 FBD XML 中的 `<Block>`、`<InputPin>`、`<OutputPin>`、`<Wire>` 元素，构建数据依赖图，拓扑排序后生成顺序 ST 代码。

### SFC (顺序功能图) → ST

```python
from src.plc import SFCConverter

if SFCConverter.has_sfc_marker(source):
    result = SFCConverter.extract_and_convert(source)
    print(result.st_code)  # 基于 CASE 的状态机
```

**转换规则：**

- 步骤 (Step) → `E_Step` 枚举类型
- 转换 (Transition) → IF 条件
- 动作 (Action) → CASE 分支
- 动作限定符：N(非保持), P(脉冲), S(置位), R(复位), L(限时), D(延迟), P1(进入脉冲), P0(退出脉冲)
- 分支/汇合 → 并行/选择逻辑

---

## 规则检查器详解

### 三级规则体系

#### 第1级：模式匹配（正则表达式，快速扫描）

| 规则 ID | 描述 | 严重程度 | 检测内容 |
|---------|------|----------|----------|
| PLC-001 | 程序中直接使用 I/O 地址 | 警告 | `%Q0.0`, `%I0.3` 等绝对地址 |
| PLC-003 | 硬编码魔数 | 警告 | 字面数字 1500, 100 等 |
| PLC-005 | 不安全的类型转换 | 信息 | 隐式或显式类型转换 |
| PLC-006 | 除法未检查零 | 错误 | `A / B` 无零值检查 |
| PLC-010 | 不安全的字符串操作 | 警告 | CONCAT 等无长度检查 |
| PLC-011 | 浮点数相等比较 | 警告 | `IF x = 25.0` 应用 `ABS(x - 25.0) < 0.01` |
| PLC-012 | 指针解引用无空检查 | 错误 | 指针操作前未验证 |
| PLC-020 | 使用 GOTO 语句 | 警告 | 非结构化跳转 |
| PLC-021 | 空的控制分支 | 信息 | `IF ... THEN /* 空 */ END_IF` |
| PLC-022 | 循环中的 EXIT | 信息 | EXIT 语句使用 |
| PLC-025 | PROGRAM 中使用 RETURN | 警告 | RETURN 在主程序中 |

#### 第2级：结构分析（需要解析 ST 语义）

| 规则 ID | 描述 | 严重程度 | 检测内容 |
|---------|------|----------|----------|
| PLC-002 | 缺少看门狗定时器 | 警告 | 周期程序无超时监控 |
| PLC-004 | 数组访问无边界检查 | 警告 | `Data[i]` 无范围验证 |
| PLC-013 | 变量命名不规范 | 信息 | 未遵循 PLCopen i_/o_ 前缀 |
| PLC-014 | 变量无初始值 | 信息 | `VAR x : INT;` 无 `:= 0` |
| PLC-015 | 函数块超过 200 行 | 警告 | 单个块过大 |
| PLC-016 | I/O 变量缺少注释 | 信息 | 物理 I/O 无说明 |
| PLC-023 | 嵌套深度超过 4 层 | 警告 | IF/CASE 嵌套过深 |
| PLC-024 | 未使用的变量 | 信息 | 声明但未引用 |

#### 第3级：语义分析（深度逻辑检查）

| 规则 ID | 描述 | 严重程度 | 检测内容 |
|---------|------|----------|----------|
| PLC-007 | 输出无联锁保护 | 警告 | `Motor := Start;` 无安全条件 |
| PLC-008 | 输出竞态条件 | 错误 | 同一周期内多次写同一输出 |
| PLC-009 | 缺少急停处理 | 错误 | 物理 BOOL 输出无 E-Stop 检查 |
| PLC-017 | 传感器无范围校验 | 警告 | 模拟量输入未做范围检查 |
| PLC-018 | 通信无超时处理 | 错误 | 通信调用无超时机制 |
| PLC-019 | 输出无故障安全默认值 | 警告 | 输出在异常时无安全状态 |

---

## 控制流图分析

对 ST 代码构建控制流图 (CFG)，进行深度语义分析：

```python
from src.plc import CFGAnalyzer

source = '''
PROGRAM Main
VAR
    x : INT := 0;
    y : INT;
END_VAR
IF x > 0 THEN
    y := x * 2;
END_IF;
y := 999;  // 死代码：y 被立即覆盖
END_PROGRAM
'''

findings = CFGAnalyzer.analyze(source)
for f in findings:
    print(f"[{f['rule_id']}] {f['severity']}: {f['description']}")
```

**分析能力：**

| 发现 | ID | 原理 |
|------|-----|------|
| 不可达代码 | CFG-001 | 基本块无入边（BFS 遍历） |
| 无出口循环 | CFG-002 | 检测回边，分析循环退出条件 |
| 先使用后定义 | CFG-003 | 变量定义-使用链 (def-use chain) |
| 死代码存储 | CFG-004 | 变量赋值后从未被读取 |
| 高圈复杂度 | CFG-005 | 圈复杂度 >15 的函数块 |

---

## 硬件配置验证

自动解析 TIA Portal 硬件配置 XML，验证安全性和可靠性：

```python
from src.plc.hw_config import HWConfigParser, HWConfigRulesChecker

# 解析硬件配置
config = HWConfigParser.parse_file("HWConfig.xml")

print(f"CPU 型号: {config.cpu.model}")
print(f"固件版本: {config.cpu.firmware_version}")
print(f"保护等级: {config.cpu.protection_level}")
print(f"看门狗: {config.cpu.cycle_watchdog_ms}ms")
print(f"Web 服务器: {config.cpu.web_server_enabled}")
print(f"安全 CPU: {config.cpu.is_safety_cpu}")
print(f"I/O 模块数: {len(config.io_modules)}")
print(f"网络接口数: {len(config.networks)}")

# 运行验证规则
violations = HWConfigRulesChecker.check(config)
for v in violations:
    print(f"[{v.rule_id}] {v.severity}: {v.description}")
    print(f"  建议: {v.suggestion}")
```

**验证规则：**

| 规则 | 描述 | 严重程度 |
|------|------|----------|
| HW-001 | CPU 固件存在已知漏洞 (CVE) | 严重 |
| HW-002 | CPU 保护等级过低 (Level 0) | 错误 |
| HW-003 | 周期看门狗禁用或过长 (>500ms) | 警告 |
| HW-004 | 安全 I/O 无冗余配置 | 警告 |
| HW-005 | 安全 CPU 未配置安全程序 | 错误 |
| HW-006 | PROFINET 未启用端口安全 | 警告 |
| HW-007 | 安全 CPU 未设置密码 | 严重 |
| HW-008 | Web 服务器使用 HTTP (非 HTTPS) | 警告 |
| HW-009 | 使用未加密通信协议 (S7comm) | 警告 |
| HW-010 | 安全看门狗与标准看门狗不匹配 | 警告 |
| HW-011 | CPU 内存过小 | 信息 |
| HW-012 | CPU 订货号与型号不匹配 | 信息 |

---

## LLM 微调数据管道

### 数据来源

| 来源 | 说明 | 数量 |
|------|------|------|
| 规则库 | 每条规则 → 违规/修复代码对 | ~30 条 |
| 漏洞数据库 | 20+ CWE 映射的 PLC 漏洞模式 | ~40 条 |
| Few-shot | 精选 (坏代码, 审查意见, 修复代码) 三元组 | 3+ 条 |
| 代码库扫描 | 真实代码 → 规则检查 → 训练对 | 无上限 |

### 漏洞模式库 (20+ CWE)

包含以下漏洞类型（每个都有详细的漏洞代码、修复代码和 IEC 标准引用）：

| CWE | 漏洞名称 | 严重程度 |
|-----|----------|----------|
| CWE-482 | 比较和赋值混淆 (`=` vs `:=`) | 错误 |
| CWE-119 | 数组越界访问 | 严重 |
| CWE-670 | 输出竞态条件 | 错误 |
| CWE-250 | 不必要的高权限执行 | 严重 |
| CWE-362 | 共享变量无同步 | 错误 |
| CWE-190 | 整数溢出 | 错误 |
| CWE-369 | 除零错误 | 严重 |
| CWE-478 | CASE 缺少默认分支 | 警告 |
| CWE-798 | 硬编码凭据 | 严重 |
| CWE-676 | 使用危险函数 (GOTO) | 警告 |
| CWE-457 | 使用未初始化变量 | 错误 |
| CWE-835 | 无限循环 | 严重 |
| CWE-628 | 函数调用参数错误 | 错误 |
| CWE-120 | 字符串缓冲区溢出 | 错误 |
| CWE-195 | 有符号/无符号转换错误 | 警告 |
| CWE-665 | 初始化不当 | 警告 |
| CWE-820 | 缺少同步机制 | 错误 |
| CWE-284 | 访问控制不当 | 严重 |
| CWE-311 | 敏感数据未加密 | 错误 |
| CWE-693 | 保护机制失效 | 严重 |
| CWE-754 | 异常条件检查不足 | 警告 |

### 命令行使用

```powershell
# 基础用法：从规则库生成
python -m src.plc.finetune.cli --output ./data/training.jsonl

# 从真实代码库生成（会运行规则检查器 + CFG 分析器）
python -m src.plc.finetune.cli --repo "D:\MyPLCProject" --output ./data/training.jsonl

# 指定格式
python -m src.plc.finetune.cli --format jsonl --output ./data/train.jsonl
python -m src.plc.finetune.cli --format alpaca --output ./data/train.json
python -m src.plc.finetune.cli --format sharegpt --output ./data/train.json

# 自动划分训练/验证/测试集 (80%/10%/10%)
python -m src.plc.finetune.cli --split --output-dir ./data/

# 打印统计信息
python -m src.plc.finetune.cli --stats
```

### Python API 使用

```python
from src.plc.finetune import DatasetGenerator, PLCPromptBuilder, DomainContext

# === 生成数据集 ===
gen = DatasetGenerator()

# 从所有来源生成
examples = gen.generate_all(repo_path="D:\\MyPLCProject")
print(f"总共生成 {len(examples)} 条训练数据")

# 划分数据集
train, val, test = gen.split_dataset(examples, train_ratio=0.8)
print(f"训练集: {len(train)}, 验证集: {len(val)}, 测试集: {len(test)}")

# 导出
gen.export_jsonl(train, "train.jsonl")
gen.export_jsonl(val, "val.jsonl")
gen.export_jsonl(test, "test.jsonl")

# === 构建专业 Prompt ===
builder = PLCPromptBuilder()

# 通用代码审查 prompt
prompt = builder.build_system_prompt("general")

# 安全审查 prompt（带 SIL 等级）
prompt = builder.build_safety_review_prompt(code, safety_level="SIL2")

# 链式思维 prompt（逐步分析）
prompt = builder.build_chain_of_thought_prompt(code)

# 定向漏洞搜索 prompt
prompt = builder.build_vulnerability_prompt(code, "buffer overflow")

# Few-shot prompt（带示例）
prompt = builder.build_few_shot_prompt(code)

# === 访问领域知识 ===
# 漏洞模式库
patterns = DomainContext.get_vulnerability_patterns()
for p in patterns:
    print(f"{p.cwe_id}: {p.name} ({p.severity})")

# PLCopen 编码规范
guidelines = DomainContext.get_review_guidelines()
for g in guidelines:
    print(f"{g.rule_id}: {g.title}")

# 厂商特有行为
quirks = DomainContext.get_vendor_quirks()
for vendor, notes in quirks.items():
    print(f"\n{vendor}:")
    for note in notes:
        print(f"  - {note}")

# IEC 标准引用
refs = DomainContext.get_standard_references()
for topic, ref in refs.items():
    print(f"{topic}: {ref}")
```

---

## 外部工具集成

工具会自动检测已安装的外部 PLC 分析工具并运行：

| 工具 | 检测方式 | 功能 |
|------|----------|------|
| **IEC Checker** | `iec-checker` 在 PATH 中 | IEC 61131-3 合规检查、类型检查、死代码检测 |
| **plc-lint** | `plc-lint` 在 PATH 中 | 轻量级 ST 代码检查 |
| **CODESYS CLI** | 常见安装路径 | CODESYS 分析 (占位) |
| **自定义工具** | 可配置 | 任何输出行格式警告的工具 |

### 添加自定义工具

```python
from src.plc import ExternalAnalyzer, GenericTool

# 创建自定义工具
my_tool = GenericTool(
    tool_name="MyPLCChecker",
    command=["my-plc-checker", "--format", "line", "{file}"],
)

# 添加到分析器
analyzer = ExternalAnalyzer(extra_tools=[my_tool])
violations = analyzer.analyze("path/to/code.st")
```

---

## 支持的编程语言（28种）

工具支持 28 种编程语言，其中 23 种支持 Tree-sitter AST 解析以提取深层代码上下文：

| 语言 | 扩展名 | AST 支持 |
|------|--------|----------|
| Python | `.py` | Tree-sitter |
| JavaScript | `.js`, `.jsx` | Tree-sitter |
| TypeScript | `.ts`, `.tsx` | Tree-sitter |
| Java | `.java` | Tree-sitter |
| Go | `.go` | Tree-sitter |
| Rust | `.rs` | Tree-sitter |
| C | `.c`, `.h` | Tree-sitter |
| C++ | `.cpp`, `.hpp` | Tree-sitter |
| C# | `.cs` | Tree-sitter |
| PHP | `.php` | Tree-sitter |
| Ruby | `.rb` | Tree-sitter |
| Swift | `.swift` | Tree-sitter |
| Kotlin | `.kt`, `.kts` | Tree-sitter |
| Scala | `.scala`, `.sc` | Tree-sitter |
| Lua | `.lua` | Tree-sitter |
| SQL | `.sql` | Tree-sitter |
| Julia | `.jl` | Tree-sitter |
| MATLAB | `.m` | Tree-sitter |
| Solidity | `.sol` | Tree-sitter |
| Shell/Bash | `.sh`, `.bash`, `.zsh` | Tree-sitter |
| Verilog/SystemVerilog | `.v`, `.vh`, `.sv`, `.svh` | Tree-sitter |
| Zig | `.zig` | Tree-sitter |
| Objective-C | `.mm` | Tree-sitter |
| Dart | `.dart` | 仅 LLM |
| Structured Text (PLC) | `.st`, `.iecst` | 仅 LLM |
| COBOL | `.cob`, `.cbl`, `.cpy` | 仅 LLM |
| R | `.r` | 仅 LLM |
| SAS | `.sas` | 仅 LLM |

**AST 支持**表示工具使用 Tree-sitter 提取变更行周围的函数、类、导入和相关符号。标记为"仅 LLM"的语言仍然会获得完整的 LLM 审查 — 工具会将完整源代码和 diff 发送给模型。

---

## 配置参数说明

在 `.env` 文件中配置，或通过环境变量设置：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | — | Anthropic API 密钥 |
| `ANTHROPIC_BASE_URL` | — | 自定义 API 端点（见[模型配置](#模型配置)） |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | 使用的模型 ID |
| `DISABLE_THINKING` | `false` | 禁用 thinking 模式（Mimo 等推理模型需要） |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | RAG 用的嵌入模型 |
| `VECTORSTORE_DIR` | `./data/vectorstore` | ChromaDB 向量数据库路径 |
| `CONFIDENCE_THRESHOLD` | `0.6` | 最低置信度阈值（低于此值的发现被过滤） |
| `MAX_CONTEXT_TOKENS` | `8000` | 上下文 token 预算 |
| `TEMPERATURE` | `0.0` | LLM 温度参数 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `CUSTOM_GUIDELINES_DIR` | `./data/custom_guidelines` | 自定义知识库上传目录 |
| `MAX_UPLOAD_SIZE_MB` | `10` | 知识库文件最大上传大小 (MB) |

---

## 项目结构

```
intelligent-code-review-agent/
├── src/
│   ├── main.py                    # CLI 入口
│   ├── config.py                  # 配置管理 (pydantic-settings)
│   ├── agent/
│   │   ├── review_agent.py        # 主审查编排器 (CodeReviewAgent)
│   │   └── prompts.py             # LLM 系统 prompt 和模板
│   ├── parsing/
│   │   ├── context_builder.py     # 文件读取 + 上下文组装
│   │   ├── ast_extractor.py       # 语言无关的 AST 提取（28 种语言）
│   │   ├── diff_parser.py         # Git diff 解析
│   │   └── language_support.py    # Tree-sitter 语言加载（23 种语法）
│   ├── plc/                       # 工业 PLC 分析（核心）
│   │   ├── simatic_parser.py      # 西门子 TIA Portal (SimaticML)
│   │   ├── twincat_parser.py      # 倍福 TwinCAT 3 (TcPOU)
│   │   ├── codesys_parser.py      # CODESYS V3 (WAGO, Schneider 等)
│   │   ├── rockwell_parser.py     # 罗克韦尔 (L5X)
│   │   ├── abb_parser.py          # ABB Automation Builder
│   │   ├── ge_parser.py           # GE/Fanuc Proficy Machine Edition
│   │   ├── omron_parser.py        # 欧姆龙 Sysmac Studio (.smc2)
│   │   ├── xml_parser.py          # 通用 PLC XML 回退解析
│   │   ├── ld_converter.py        # 梯形图 → ST
│   │   ├── fbd_converter.py       # 功能块图 → ST
│   │   ├── sfc_converter.py       # 顺序功能图 → ST
│   │   ├── st_extractor.py        # ST 变量/函数提取器
│   │   ├── plc_rules.py           # 30+ PLC 规则 (3 级)
│   │   ├── cfg_analyzer.py        # 控制流图分析
│   │   ├── external_analyzer.py   # 外部工具集成
│   │   ├── hw_config.py           # 硬件配置解析 + 验证
│   │   └── finetune/              # LLM 微调数据管道
│   │       ├── domain_context.py      # IEC 61131-3 领域知识库
│   │       ├── prompt_builder.py      # PLC 专用 prompt 工程
│   │       ├── dataset_generator.py   # 训练数据生成
│   │       └── cli.py                 # 微调 CLI 入口
│   ├── output/
│   │   ├── models.py              # ReviewComment, ReviewReport 模型
│   │   ├── severity.py            # 严重程度分类
│   │   └── formatter.py           # 输出格式化 (JSON/Markdown)
│   ├── rag/
│   │   ├── retriever.py           # ChromaDB 指南检索
│   │   └── loader.py              # 文档加载
│   ├── git/
│   │   ├── reader.py              # Git diff 提取
│   │   ├── repo_manager.py        # Git 仓库管理
│   │   └── models.py              # DiffResult 模型
│   └── config.py                  # 配置 (pydantic-settings)
├── api/                           # FastAPI 后端
│   ├── main.py                    # 应用设置、CORS、静态文件
│   ├── models.py                  # Pydantic 请求/响应模型
│   └── routes/
│       ├── scan.py                # 扫描任务管理端点
│       ├── report.py              # 报告检索端点
│       ├── file_scan.py           # 单文件上传扫描
│       ├── guidelines.py          # 知识库 CRUD + 向量索引
│       └── config.py              # 配置和语言列表端点
├── web/                           # Vue 3 前端
│   ├── src/
│   │   ├── App.vue                # 侧边栏导航布局
│   │   ├── main.ts                # Vue 应用入口
│   │   ├── router/index.ts        # 客户端路由
│   │   ├── stores/                # Pinia 状态管理
│   │   │   └── scan.ts            # 扫描任务状态 + API 调用
│   │   ├── services/
│   │   │   └── api.ts             # Axios API 客户端 + 类型定义
│   │   ├── views/
│   │   │   ├── HomeView.vue       # 仪表盘（报告列表）
│   │   │   ├── ScanView.vue       # 新建扫描表单 + 进度追踪
│   │   │   ├── FileScanView.vue   # 拖拽文件扫描
│   │   │   ├── ReportView.vue     # 完整报告查看器
│   │   │   ├── CompareView.vue    # 报告并排对比
│   │   │   ├── GuidelinesView.vue # 知识库文件管理
│   │   │   └── SettingsView.vue   # 配置和语言显示
│   │   ├── components/
│   │   │   └── LanguageSwitcher.vue  # UI 语言切换器
│   │   └── locales/               # i18n 翻译
│   │       ├── en.ts              # 英语
│   │       ├── zh.ts              # 中文
│   │       ├── de.ts              # 德语
│   │       └── cs.ts              # 捷克语
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── tests/                         # 测试套件 (107 个测试)
│   ├── test_diff_parser.py        # Diff 解析测试
│   ├── test_output_models.py      # 输出模型测试
│   ├── test_review_agent.py       # 审查 Agent 测试
│   ├── test_ast_extractor.py      # AST 提取测试
│   ├── test_rag.py                # RAG 测试
│   ├── test_fbd_converter.py      # FBD 转换测试
│   ├── test_hw_config.py          # 硬件配置测试
│   └── test_finetune.py           # 微调管道测试
├── data/
│   ├── guidelines/                # RAG 知识库 (Markdown)
│   │   ├── clean_code_principles.md
│   │   ├── python_best_practices.md
│   │   └── security_checklist.md
│   ├── plc/
│   │   ├── plcopen_guidelines.md  # PLCopen 编码规范
│   │   └── secure_plc_practices.md # PLC 安全实践
│   └── vectorstore/               # ChromaDB 向量数据库
├── docs/
├── pyproject.toml                 # 项目配置
├── README.md                      # 英文文档
├── README_CN.md                   # 中文文档（本文件）
└── .env                           # API 密钥 + 配置
```

---

## 运行测试

```powershell
# 运行全部测试
python -m pytest tests/ -v

# 运行特定模块测试
python -m pytest tests/test_hw_config.py -v       # 硬件配置
python -m pytest tests/test_fbd_converter.py -v    # FBD 转换
python -m pytest tests/test_finetune.py -v         # 微调管道
python -m pytest tests/test_review_agent.py -v     # 审查 Agent

# 只运行失败的测试
python -m pytest tests/ --lf

# 显示覆盖率
python -m pytest tests/ --tb=short -q
```

---

## 市场覆盖率

| 地区 | 覆盖厂商 | 估计市场份额 |
|------|----------|-------------|
| **欧洲** | 西门子, 倍福, CODESYS (WAGO, Schneider, ABB AC500, Bosch Rexroth, Phoenix Contact) | ~96% |
| **美洲** | 罗克韦尔/Allen-Bradley, GE/Fanuc, 西门子 | ~96% |
| **亚太** | 欧姆龙, 三菱 (不支持), 西门子 | ~85% |

---

## 常见问题

### Q: 如何只审查 PLC 文件，不审查 Python 等其他语言？

工具会自动根据文件扩展名判断语言。`.st`、`.iecst` 和 PLC 相关的 `.xml` 文件会被自动识别为 PLC 代码并执行深度分析。其他语言（Python、JS 等）只会进行 LLM 审查。

### Q: 我的 CODESYS 项目是 ZIP 压缩包，能直接审查吗？

目前不支持直接读取 ZIP。需要先解压，然后指向包含 XML 的目录。Omron 的 `.smc2` 格式（也是 ZIP）已支持自动解压。

### Q: 如何添加自定义审查规则？

在 `src/plc/plc_rules.py` 的 `PATTERN_RULES` 列表中添加新规则：

```python
PATTERN_RULES.append({
    "id": "PLC-CUSTOM-001",
    "name": "My custom rule",
    "pattern": r"your_regex_here",
    "severity": "warning",
    "description": "Description of the issue",
    "suggestion": "How to fix it",
})
```

### Q: 微调数据生成后，用什么模型微调？

- **JSONL 格式**：适用于 OpenAI GPT 系列、Anthropic Claude 微调
- **Alpaca 格式**：适用于 LLaMA、Qwen 等开源模型
- **ShareGPT 格式**：适用于 Vicuna、ChatGLM 等对话模型

### Q: 硬件配置验证支持哪些 PLC 品牌？

目前只支持 **西门子 TIA Portal** 的 HWConfig XML 格式。其他品牌的硬件配置验证将在后续版本中添加。

---

## License

MIT
