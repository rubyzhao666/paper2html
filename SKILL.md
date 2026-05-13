---
name: paper2html
description: 学术论文PDF → 可视化HTML阅读器，支持arXiv链接、多粒度AI摘要、3套视觉主题
version: 1.0.0
tags:
  - academic
  - paper
  - pdf
  - html
  - arxiv
  - visualization
---

# paper2html Skill

**学术论文 → 可视化HTML阅读器**

将学术论文（PDF文件或arXiv链接）一键转换为精美的交互式HTML阅读器，支持AI智能摘要、多粒度导航、公式渲染和主题切换。

## 产品概述

### 核心价值

- **一键转换**：从 PDF 到精美 HTML，只需一条命令
- **arXiv原生支持**：直接传入 arXiv 链接，自动下载+解析+转换
- **AI智能摘要**：自动生成 TL;DR、三分钟摘要、章节摘要
- **精美可视化**：公式（KaTeX）、架构图（Mermaid）、图片内嵌
- **多套主题**：深色实验室 / 纯净纸张 / 霓虹科技

### 适用场景

- 论文阅读和分享
- 学术报告辅助
- 文献综述整理
- 知识库建设

---

## 快速开始

### 1. 安装依赖

```bash
cd paper2html
pip install -r requirements.txt
```

### 2. 配置 API Key

**Doc2X API**（解析层，必需）：
- 获取地址：https://pdf2x.cn/api/apikey
- 环境变量：`DOC2X_APIKEY`

**DeepSeek API**（理解层，推荐）：
- 获取地址：https://platform.deepseek.com/api_keys
- 环境变量：`DEEPSEEK_API_KEY`

```bash
export DOC2X_APIKEY="your-doc2x-key"
export DEEPSEEK_API_KEY="your-deepseek-key"
```

### 3. 一条命令使用

```bash
# 基本用法
python paper2html.py --input paper.pdf --output output.html

# arXiv 链接
python paper2html.py --input https://arxiv.org/abs/1706.03762 --output attention.html

# 切换主题
python paper2html.py --input paper.pdf --style neon_tech --output output.html

# 跳过 AI 理解（快速预览）
python paper2html.py --input paper.pdf --no-understand --output output.html
```

### 4. 运行验证脚本（确认安装成功）

```bash
python scripts/verify.py
```

完整的验收测试步骤参见 [references/acceptance-test-guide.md](references/acceptance-test-guide.md)。

## Critical Bug Verification (MUST CHECK)

**Markdown → HTML Conversion**: The renderer MUST convert Markdown syntax to proper HTML before inserting into the template. If Markdown is passed directly as raw text, headers/bold/italics/tables will not render.

Verification:
```python
from rendering.renderer import PaperRenderer

r = PaperRenderer()
html = r._markdown_to_html("# Test\n\n**Bold** text.")
assert "<h1" in html or "<h1 " in html, "Markdown headers not converted"
assert "<strong>" in html, "Bold text not converted"
```

**Known Pitfall**: Missing `import markdown` at the top of `rendering/renderer.py` causes silent failures. The import statement MUST be present.

---

## 三层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         paper2html                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   解析层    │ →  │   理解层    │ →  │   渲染层    │        │
│  │  (parsers)  │    │ (understanding)│  │ (rendering) │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│        ↓                  ↓                  ↓                 │
│   Doc2X API         LLM API          HTML/CSS/JS              │
│   PPX 本地          DeepSeek         KaTeX/Mermaid             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 解析层 (parsers/)

**功能**：将 PDF 转换为结构化 Markdown

| 模块 | 说明 |
|------|------|
| `doc2x_parser.py` | Doc2X API 解析器（主方案） |
| `ppx_parser.py` | 本地 PPX 解析器（备选） |
| `arxiv_handler.py` | arXiv 链接处理和 PDF 下载 |

```python
from parsers import Doc2XParser, ArxivHandler

# 解析本地 PDF
parser = Doc2XParser()
result = parser.parse("paper.pdf")

# 处理 arXiv
handler = ArxivHandler()
pdf_path, arxiv_id, metadata = handler.download_and_prepare("https://arxiv.org/abs/2402.19473")
```

### 理解层 (understanding/)

**功能**：AI 理解论文内容，生成多粒度摘要

| 模块 | 说明 |
|------|------|
| `chunker.py` | Markdown 分片器 |
| `llm_client.py` | LLM API 客户端 |
| `prompts.py` | Prompt 模板 |

```python
from understanding import PaperUnderstanding

understander = PaperUnderstanding()
result = understander.understand(parse_result)

print(result.tldr)              # 一句话核心贡献
print(result.key_findings)      # 三分钟摘要
print(result.section_summaries) # 章节摘要
print(result.mermaid_code)      # Mermaid 架构图
```

### 渲染层 (rendering/)

**功能**：将解析+理解结果渲染为 HTML

| 模块 | 说明 |
|------|------|
| `renderer.py` | 主渲染器 |
| `styles.py` | 样式预设 |
| `templates.py` | HTML 模板 |

```python
from rendering import PaperRenderer

renderer = PaperRenderer(style="dark_lab")
renderer.render(parse_result, understanding_result, "output.html")
```

---

## CLI 用法

### 完整参数

```bash
python paper2html.py [选项]

选项:
  --input, -i          输入文件路径或arXiv链接（必需）
  --output, -o         输出HTML路径（默认自动生成）
  --style, -s          样式预设: dark_lab|clean_paper|neon_tech
  --api-key            Doc2X API密钥
  --llm-api-key        LLM API密钥
  --llm-base-url       LLM API Base URL
  --llm-model          LLM模型名
  --no-understand      跳过理解层
  --debug              调试模式
```

### 示例

```bash
# 完整转换（推荐配置）
python paper2html.py \
  --input paper.pdf \
  --output output.html \
  --style dark_lab

# arXiv 链接
python paper2html.py --input https://arxiv.org/abs/2402.19473

# 快速预览（跳过AI理解）
python paper2html.py --input paper.pdf --no-understand

# 指定API Key
python paper2html.py \
  --input paper.pdf \
  --api-key sk-xxx \
  --llm-api-key sk-xxx
```

---

## Python API 用法

### 方式一：一条命令

```python
from paper2html import convert_paper

output_path = convert_paper(
    input_path="paper.pdf",
    output_path="output.html",
    style="dark_lab"
)
```

### 方式二：类接口（灵活控制）

```python
from paper2html import Paper2HTML

# 初始化
converter = Paper2HTML(
    style="neon_tech",
    llm_model="deepseek-chat"
)

# 一站式转换
output_path = converter.convert("paper.pdf", "output.html")

# 分步使用
parse_result = converter.parse("paper.pdf")
understanding_result = converter.understand(parse_result)
html_path = converter.render(parse_result, understanding_result, "output.html")
```

### 分层使用

```python
from paper2html import parsers, understanding, rendering

# 1. 解析
parser = parsers.Doc2XParser()
parse_result = parser.parse("paper.pdf")

# 2. 理解
understander = understanding.PaperUnderstanding()
understanding_result = understander.understand(parse_result)

# 3. 渲染
renderer = rendering.PaperRenderer(style="dark_lab")
renderer.render(parse_result, understanding_result, "output.html")
```

---

## 功能清单

### 输入支持

| 功能 | 说明 |
|------|------|
| 本地 PDF | 支持解析本地 PDF 文件 |
| arXiv 链接 | 支持 abs/pdf URL 或纯 ID |
| API Key 配置 | 支持命令行和环境变量 |

### 摘要粒度

| 粒度 | 说明 |
|------|------|
| TL;DR | 一句话核心贡献 |
| 三分钟摘要 | 3个关键发现 + 创新点 + 意义 |
| 章节摘要 | 每个章节的详细摘要 |
| 结构化抽取 | 标题/作者/方法/贡献/局限等 |

### 渲染组件

| 组件 | 说明 |
|------|------|
| KaTeX 公式 | 原生支持 LaTeX 公式渲染 |
| Mermaid 图 | 自动渲染架构图 |
| 图片内嵌 | Base64 内嵌，离线可用 |
| 代码高亮 | 代码块语法高亮 |
| 目录导航 | 左侧可折叠目录 |
| 阅读模式 | 速读/标准/精读 |

### 样式预设

| 主题 | 风格 | 适用场景 |
|------|------|----------|
| `dark_lab` | 深色背景，绿色强调 | 夜间阅读 |
| `clean_paper` | 白色背景，学术蓝强调 | 打印/分享 |
| `neon_tech` | 深紫背景，霓虹强调 | 科技感展示 |

---

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DOC2X_APIKEY` | Doc2X API 密钥 | - |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | - |
| `DEEPSEEK_BASE_URL` | DeepSeek API Base URL | https://api.deepseek.com/v1 |
| `LLM_MODEL` | LLM 模型名 | deepseek-chat |

### .env 文件（可选）

```bash
# .env
DOC2X_APIKEY=sk-your-doc2x-key
DEEPSEEK_API_KEY=sk-your-deepseek-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

---

## 已知限制

1. **扫描版 PDF**：无法提取文本层，需要 OCR 预处理
2. **API 额度**：Doc2X 和 DeepSeek 都有免费额度限制
3. **复杂表格**：多级表头或合并单元格可能格式错乱
4. **arXiv 下载**：部分论文可能下载失败（网络原因）
5. **图片内嵌**：大量图片会增加 HTML 文件大小

---

## 不做功能（MVP）

- ~~OCR 扫描版 PDF~~
- ~~多论文批量处理~~
- ~~PDF 解析修复~~
- ~~论文对比功能~~
- ~~移动端原生 App~~

---

## 文件结构

```
paper2html/
├── paper2html.py              # 主入口（CLI + API）
├── parsers/                   # 解析层
│   ├── __init__.py
│   ├── doc2x_parser.py
│   ├── ppx_parser.py
│   └── arxiv_handler.py
├── understanding/              # 理解层
│   ├── __init__.py
│   ├── chunker.py
│   ├── llm_client.py
│   └── prompts.py
├── rendering/                 # 渲染层
│   ├── __init__.py
│   ├── renderer.py
│   ├── styles.py
│   └── templates.py
├── references/                # 参考文档
│   ├── api-docs.md
│   ├── cli-options.md
│   ├── style-presets.md
│   └── troubleshooting.md
├── scripts/                  # 快捷脚本
│   ├── parse.sh
│   └── generate.sh
├── test_output/              # 测试输出
├── requirements.txt
├── SKILL.md
└── README.md
```

---

## 常见问题

详见 [references/troubleshooting.md](references/troubleshooting.md)
