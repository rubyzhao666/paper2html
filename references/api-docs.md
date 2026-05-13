# Doc2X API 文档

## 概述

Doc2X API 是一个专业的文档解析服务，底层引擎为 v2.doc2x.noedgeai.com。支持将 PDF 文档解析为 Markdown、LaTeX、Word 等格式，并提取文本、公式、表格、图片等元素。

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v2/parse/preupload` | POST | 获取上传URL和uid |
| PUT (返回的URL) | PUT | 上传PDF文件 |
| `/api/v2/parse/status` | GET | 查询解析状态 |
| `/api/v2/convert/parse` | POST | 提交格式转换 |
| `/api/v2/convert/parse/result` | GET | 获取转换结果 |

## 认证

所有API请求需要在Header中包含认证信息：

```
Authorization: Bearer YOUR_API_KEY
```

API Key 获取地址：
- https://open.noedgeai.com
- https://pdf2x.cn/api/apikey/page

## API 调用流程

### Step 1: 预上传 - 获取上传URL

```http
POST /api/v2/parse/preupload
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
    "name": "paper.pdf"
}
```

**响应示例**:
```json
{
    "url": "https://storage.noedgeai.com/upload/xxx",
    "uid": "abc123xyz"
}
```

### Step 2: 上传PDF文件

使用Step 1返回的URL，直接PUT上传PDF文件：

```http
PUT https://storage.noedgeai.com/upload/xxx
Content-Type: application/pdf

[PDF二进制数据]
```

**响应**: HTTP 200/201 表示成功

### Step 3: 轮询解析状态

```http
GET /api/v2/parse/status?uid=abc123xyz
Authorization: Bearer YOUR_API_KEY
```

**响应示例**:
```json
{
    "status": "success",  // pending, processing, success, error
    "progress": 100,
    "error": null
}
```

建议轮询间隔：
- 开始：2秒
- 递增：乘以1.5
- 最大：10秒
- 超时：5分钟

### Step 4: 提交格式转换

```http
POST /api/v2/convert/parse
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
    "uid": "abc123xyz",
    "to": "md",           // md, tex, docx
    "formula_mode": "dollar"  // dollar, latex
}
```

**参数说明**：
| 参数 | 可选值 | 说明 |
|------|--------|------|
| `to` | `md`, `tex`, `docx` | 输出格式 |
| `formula_mode` | `dollar`, `latex` | 公式格式：dollar用$...$，latex用\begin{} |

### Step 5: 获取转换结果

```http
GET /api/v2/convert/parse/result?uid=def456uvw
Authorization: Bearer YOUR_API_KEY
```

**响应示例**:
```json
{
    "status": "success",
    "url": "https://storage.noedgeai.com/download/xxx/result.zip"
}
```

### Step 6: 下载结果

下载Step 5返回的URL，解压获取结果文件。

## 输出格式

### Markdown ($...$ 公式格式)

```markdown
# 标题

这是正文，包含行内公式 $E = mc^2$。

块公式：
$$
\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
$$

## 表格

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 数据 | 数据 | 数据 |

## 图片

![描述](./images/fig1.png)
```

### Markdown (LaTeX环境格式)

```markdown
# 标题

这是正文，包含行内公式 \(E = mc^2\)。

块公式：
\begin{equation}
\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
\end{equation}
```

### JSON格式 (v3-2026模型)

```json
{
    "title": "论文标题",
    "authors": [
        {"name": "作者1", "affiliation": "机构1"},
        {"name": "作者2", "affiliation": "机构2"}
    ],
    "abstract": "摘要内容...",
    "sections": {
        "introduction": {
            "heading": "1. Introduction",
            "content": "正文...",
            "subsections": {...}
        }
    },
    "references": [
        {
            "id": 1,
            "title": "引用标题",
            "authors": ["..."],
            "venue": "期刊/会议",
            "year": 2024
        }
    ],
    "figures": [
        {"id": 1, "caption": "图1描述", "path": "./images/fig1.png"}
    ],
    "tables": [...],
    "formulas": [...]
}
```

## 错误码

| HTTP状态码 | 错误码 | 说明 | 处理建议 |
|------------|--------|------|----------|
| 400 | `invalid_file` | 文件格式错误 | 检查PDF是否损坏 |
| 401 | `unauthorized` | API Key无效 | 检查Key是否正确 |
| 403 | `quota_exceeded` | 额度不足 | 购买套餐或等待重置 |
| 404 | `not_found` | 文件/资源不存在 | 重新上传 |
| 429 | `rate_limit` | 请求过于频繁 | 降低请求频率 |
| 500 | `internal_error` | 服务器内部错误 | 稍后重试 |
| 503 | `service_unavailable` | 服务暂时不可用 | 等待后重试 |

## 定价

| 套餐 | 价格 | 页数 | 说明 |
|------|------|------|------|
| 免费试用 | ¥0 | 50页 | 首次注册赠送 |
| 按量付费 | ¥0.005/页 | 无限制 | 即用即付 |
| 月度套餐 | ¥29/月 | 5000页 | 适合个人用户 |
| 年度套餐 | ¥199/年 | 20000页/年 | 适合重度用户 |

*定价可能有变动，请以官网为准*

## Python SDK 使用

推荐使用 pdfdeal 库：

```python
from pdfdeal import Doc2X

client = Doc2X(apikey="YOUR_API_KEY")

# 方式1: 解析PDF
success, failed, flag = client.pdf2file(
    pdf_file="paper.pdf",
    output_path="./output",
    output_format="md_dollar",  # md_dollar, md, tex, docx
    model="v3-2026",             # 可选，默认v2
)

# 方式2: 解析并获取结果对象
success, content, images = client.pdf2md(
    pdf_file="paper.pdf",
    formula_mode="dollar",
)
```

## 注意事项

1. **文件大小限制**: 单个PDF建议不超过50MB
2. **页数限制**: 单次解析建议不超过200页
3. **图片提取**: 需确认PDF包含可提取的图片（非扫描版）
4. **公式识别**: v3-2026模型公式识别效果更好
5. **并发限制**: 免费用户建议控制并发，付费用户无限制
6. **数据安全**: 上传的PDF会在24小时内自动删除

## 常见问题

详见 `references/troubleshooting.md`
