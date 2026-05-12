**paper2html**
学术论文 → 可视化HTML阅读器
将学术论文（PDF或arXiv链接）一键转换为精美的交互式HTML阅读器，支持AI智能摘要、多粒度导航、公式渲染和主题切换。

**特性**

🚀 一键转换：PDF/arXiv → HTML，一条命令搞定
📚 arXiv原生支持：直接传入arXiv链接
🤖 AI智能摘要：自动生成TL;DR、三分钟摘要、章节摘要
🎨 三套精美主题：深色实验室 / 纯净纸张 / 霓虹科技
📐 公式渲染：KaTeX原生支持LaTeX公式
🔄 Mermaid图：自动渲染架构图
📱 响应式设计：移动端适配
快速开始

**安装**
bash
cd Skills开发/paper2html
pip install -r requirements.txt
配置API Key
bash
# Doc2X API（解析用）
export DOC2X_APIKEY="your-doc2x-key"

# DeepSeek API（理解用）
export DEEPSEEK_API_KEY="your-deepseek-key"
使用
bash
# 基本用法
python paper2html.py --input paper.pdf --output output.html

# arXiv链接
python paper2html.py --input https://arxiv.org/abs/1706.03762

# 切换主题
python paper2html.py --input paper.pdf --style neon_tech

# 快速预览（跳过AI理解）
python paper2html.py --input paper.pdf --no-understand
Python API

python
from paper2html import convert_paper

# 一条命令
convert_paper("paper.pdf", "output.html", style="dark_lab")
详细文档

SKILL.md - 完整技能文档
references/cli-options.md - CLI参数详解
references/style-presets.md - 样式预设详解
references/troubleshooting.md - 常见问题排查
项目结构

plaintext
paper2html/
├── paper2html.py          # 主入口
├── parsers/               # 解析层
├── understanding/          # 理解层
├── rendering/             # 渲染层
├── references/            # 参考文档
├── scripts/               # 快捷脚本
└── test_output/           # 测试输出
测试论文推荐

表格
论文	arXiv ID	特点
Attention Is All You Need	1706.03762	经典Transformer
LightRAG	2402.19473	近期热门RAG
Mamba	2312.12456	公式密集
License

MIT
