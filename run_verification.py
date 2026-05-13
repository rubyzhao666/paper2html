"""paper2html 三项修复完整验证"""
import os, sys, re

# 使用相对路径而非硬编码
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

print("=" * 65)
print("  paper2html — 修复验证")
print("=" * 65)

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name} — {detail}")
        failed += 1

# Fix #1
print("\n▶ Fix #1：ParseResult 统一到 parsers/models.py")
from parsers import ParseResult, Doc2XParser, PPXParser, ArxivHandler
test("parsers 包导入成功", True)
pr = ParseResult(markdown="# Test", success=True, images=["fig1.png"])
test("ParseResult dataclass 实例化", pr.markdown == "# Test" and pr.success)
test("ParseResult 字段完整性", hasattr(pr, 'json_data') and hasattr(pr, 'metadata'))
from parsers.models import ParseResult as ModelsPR
test("ParseResult 是同一类对象 (is)", ParseResult is ModelsPR)
for fname in ["doc2x_parser.py", "ppx_parser.py"]:
    with open(f"parsers/{fname}") as f:
        text = f.read()
    dup = re.search(r'@dataclass\s+class ParseResult:', text)
    test(f"{fname} 无重复定义", dup is None)
import parsers
test("__all__ 导出完整", {"Doc2XParser","ParseResult","PPXParser","ArxivHandler"}.issubset(set(parsers.__all__)))
test(f"版本号: {parsers.__version__}", parsers.__version__ == "1.0.0")

# Fix #2
print("\n▶ Fix #2：Renderer Markdown->HTML 转换")
from rendering.renderer import PaperRenderer
renderer = PaperRenderer(style="dark_lab")
test("PaperRenderer 初始化成功", True)

md_input = "# 标题\n\n这是 **粗体** 文字。\n\n## 子标题\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n- item1\n- item2\n\n$$E=mc^2$$\n\n```python\nhello\n```"""
html_output = renderer._markdown_to_html(md_input)
test("_markdown_to_html 可调用", html_output is not None and len(html_output) > 0)
test("<h1> 存在", "<h1" in html_output)
test("<strong> 存在", "<strong>" in html_output or "粗体</strong>" in html_output)
test("<table> 存在", "<table>" in html_output)
test("<li> 存在", "<li>" in html_output)
test("<pre> 存在", "<pre" in html_output)
test("空字符串处理", renderer._markdown_to_html("") == "")

try:
    import markdown
    print(f"  ℹ️ markdown v{markdown.__version__} 已安装")
except ImportError:
    print("  ℹ️ markdown 未安装，使用回退模式")

# Fix #4
print("\n▶ Fix #4：LLM max_tokens + 智能估算")
from understanding.llm_client import LLMClient
client = LLMClient()
test("LLMClient 初始化（mock模式）", True)
test("_estimate_max_tokens 存在", hasattr(client, '_estimate_max_tokens'))
t = client._estimate_max_tokens("TL;DR 一句话核心贡献")
test("TL;DR → 512", t == 512, f"got {t}")
t3 = client._estimate_max_tokens("三分钟摘要 key findings")
test("3min → 2048", t3 == 2048, f"got {t3}")
ts = client._estimate_max_tokens("结构化 mermaid experiment")
test("structured → 4096", ts == 4096, f"got {ts}")
tc = client._estimate_max_tokens("章节 section summary")
test("section → 3072", tc == 3072, f"got {tc}")
td = client._estimate_max_tokens("随便什么内容")
test("default → 4096", td == 4096, f"got {td}")
resp = client.call("sys", "test prompt")
test("mock call 正常返回", resp.success and len(resp.content) > 0)

# Bonus: E2E
print("\n▶ Bonus：端到端渲染流程测试")
r2 = PaperRenderer(style="clean_paper")
parse_result = {
    "markdown": "# Attention Is All You Need\n\n## Abstract\n\nThe dominant sequence models are based on RNN/CNN.\n\n## Introduction\n\nWe propose the **Transformer**, using only **attention**.",
    "images": [],
    "metadata": {"title": "Attention Is All You Need", "authors": ["Vaswani et al."]}
}
ur = {
    "tldr": "Transformer uses only attention mechanisms to achieve SOTA results.",
    "key_findings": {"key_findings": ["Self-attention replaces RNN"], "innovation": "First pure attention model", "significance": "Foundation of modern LLMs"},
    "section_summaries": [{"section_title": "Abstract", "summary": "Proposed Transformer", "key_points": ["Self-attention"]}],
    "structured": {
        "research_question": "Can we build seq model with only attention?",
        "methodology": "Multi-head Self-Attention",
        "contributions": ["Self-Attention", "Multi-Head"],
        "experiment_results": ["WMT EN-DE: 28.4 BLEU"],
        "limitations": ["O(n^2) complexity"],
        "future_work": "Sparse attention",
    },
    "mermaid_code": ""
}
out = "/tmp/test_p2h_e2e.html"
result_path = r2.render(parse_result, ur, out)
test("生成HTML文件", os.path.exists(result_path))
with open(result_path) as f:
    hc = f.read()
test("DOCTYPE 声明", "<!DOCTYPE html>" in hc)
test("包含标题", "Attention Is All You Need" in hc)
test("包含作者", "Vaswani" in hc)
test("包含 TL;DR", "Transformer" in hc and "SOTA" in hc)
test("<h1> 而非原始#", "<h1" in hc)
test("文件 >5KB", len(hc) > 5000)
os.remove(out)

# Summary
print("\n" + "=" * 65)
total = passed + failed
print(f"  结果: {passed}/{total} 通过 | {'ALL PASS!' if failed == 0 else str(failed) + ' FAILED'}")
print("=" * 65)
