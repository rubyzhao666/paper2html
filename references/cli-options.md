# CLI 参数详解

本文档详细说明 `paper2html.py` 命令行工具的所有参数。

## 完整参数列表

```bash
python paper2html.py [选项]
```

### 必需参数

| 参数 | 说明 |
|------|------|
| `--input`, `-i` | 输入文件路径（本地PDF）或arXiv链接（必需） |

### 输出控制

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--output`, `-o` | 输出HTML文件路径 | 自动生成 |

自动生成规则：
- 本地文件：`paper.pdf` → `paper.html`
- arXiv：`2402.19473` → `2402.19473.html`

### 样式选择

| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `--style`, `-s` | 样式预设 | `dark_lab`, `clean_paper`, `neon_tech` | `dark_lab` |

样式预设说明：

- **`dark_lab`**：深色背景，绿色强调，适合夜间阅读
- **`clean_paper`**：白色背景，学术蓝强调，适合打印和分享
- **`neon_tech`**：深紫背景，霓虹强调，科技感强

### API 配置

#### Doc2X API（解析层）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--api-key` | Doc2X API密钥 | 环境变量 `DOC2X_APIKEY` |

#### LLM API（理解层）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--llm-api-key` | LLM API密钥 | 环境变量 `DEEPSEEK_API_KEY` |
| `--llm-base-url` | LLM API Base URL | `https://api.deepseek.com/v1` |
| `--llm-model` | LLM模型名 | `deepseek-chat` |

### 执行控制

| 参数 | 说明 |
|------|------|
| `--no-understand` | 跳过理解层，只进行解析+渲染（无AI摘要） |

使用场景：
- 快速预览，不需要AI摘要
- LLM API额度不足
- 测试解析层功能

### 调试选项

| 参数 | 说明 |
|------|------|
| `--debug` | 开启调试模式，输出详细日志 |

## 使用示例

### 基本用法

```bash
# 最小命令
python paper2html.py --input paper.pdf

# 指定输出
python paper2html.py --input paper.pdf --output my_paper.html
```

### arXiv 链接

```bash
# 直接传入 arXiv URL
python paper2html.py --input https://arxiv.org/abs/1706.03762

# 指定输出文件名
python paper2html.py \
  --input https://arxiv.org/abs/2402.19473 \
  --output lightrag.html
```

### 样式切换

```bash
# 深色主题（默认）
python paper2html.py --input paper.pdf --style dark_lab

# 纯净纸张
python paper2html.py --input paper.pdf --style clean_paper

# 霓虹科技
python paper2html.py --input paper.pdf --style neon_tech
```

### API Key 配置

```bash
# 命令行指定 Doc2X Key
python paper2html.py \
  --input paper.pdf \
  --api-key sk-your-doc2x-key

# 命令行指定 LLM Key
python paper2html.py \
  --input paper.pdf \
  --llm-api-key sk-your-deepseek-key

# 组合使用
python paper2html.py \
  --input paper.pdf \
  --api-key sk-doc2x \
  --llm-api-key sk-deepseek \
  --llm-model deepseek-chat
```

### 跳过理解层

```bash
# 快速预览，不需要AI摘要
python paper2html.py --input paper.pdf --no-understand
```

### 调试模式

```bash
# 查看详细日志
python paper2html.py --input paper.pdf --debug
```

## 环境变量替代方案

如果不想每次都输入 API Key，可以设置环境变量：

```bash
# Bash
export DOC2X_APIKEY="sk-your-doc2x-key"
export DEEPSEEK_API_KEY="sk-your-deepseek-key"

# Zsh
set -x DOC2X_APIKEY "sk-your-doc2x-key"
set -x DEEPSEEK_API_KEY "sk-your-deepseek-key"
```

或者创建 `.env` 文件：

```bash
# .env
DOC2X_APIKEY=sk-your-doc2x-key
DEEPSEEK_API_KEY=sk-your-deepseek-key
```

然后在 Python 中使用：

```python
from dotenv import load_dotenv
load_dotenv()  # 加载 .env 文件
```

## 退出码

| 退出码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1 | 参数错误或转换失败 |
| 130 | 用户中断（Ctrl+C） |
