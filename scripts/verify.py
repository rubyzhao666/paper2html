#!/usr/bin/env python3
"""paper2html 完整功能验证脚本 - 冒烟测试 + 核心功能测试"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    print("=" * 60)
    print("  paper2html 完整功能验证")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    def test(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name} — {detail}")
            failed += 1
    
    # 测试 1: 模块导入
    print("\n▶ 测试 1: 核心模块导入")
    try:
        from parsers import ParseResult
        test("ParseResult 导入成功", True)
    except Exception as e:
        test("ParseResult 导入成功", False, str(e))
    
    try:
        from rendering.renderer import PaperRenderer
        test("PaperRenderer 导入成功", True)
    except Exception as e:
        test("PaperRenderer 导入成功", False, str(e))
    
    # 测试 2: Markdown → HTML 转换
    print("\n▶ 测试 2: Markdown → HTML 转换")
    try:
        renderer = PaperRenderer(style="dark_lab")
        test("PaperRenderer 初始化成功", True)
        
        test_md = """# 测试标题

## 子标题

这是 **粗体** 文本，这是 *斜体* 文本。

| 列1 | 列2 |
|-----|-----|
| A | B |

- 列表项 1
- 列表项 2
"""
        html = renderer._markdown_to_html(test_md)
        
        test("_markdown_to_html 方法存在", True)
        test("<h1> 标题", "<h1" in html)
        test("<h2> 子标题", "<h2" in html)
        test("<strong> 粗体", "<strong>" in html)
        test("<em> 斜体", "<em>" in html)
        test("<table> 表格", "<table>" in html)
        test("<li> 列表", "<li>" in html)
    except Exception as e:
        test("Markdown 转换", False, str(e))
    
    # 测试 3: 完整渲染流程
    print("\n▶ 测试 3: 完整渲染流程")
    try:
        parse_result = {
            "markdown": "# Attention Is All You Need\n\n## Abstract\n\nThe dominant sequence **transduction models** are based on complex recurrent or convolutional neural networks.",
            "images": [],
            "metadata": {"title": "Attention Is All You Need", "authors": ["Vaswani et al."]}
        }
        understanding_result = {
            "tldr": "Transformer uses only attention mechanisms.",
            "key_findings": {"key_findings": ["Self-attention replaces RNN/CNN"]},
            "section_summaries": [],
            "structured": {},
            "mermaid_code": ""
        }
        
        import tempfile
        output_path = os.path.join(tempfile.gettempdir(), "paper2html_test.html")
        result_path = renderer.render(parse_result, understanding_result, output_path)
        
        if os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            test(f"HTML 文件生成成功 ({file_size:,} bytes)", True)
            
            with open(result_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            test("DOCTYPE 声明", "<!DOCTYPE html>" in content)
            test("论文标题存在", "Attention Is All You Need" in content)
            test("Markdown 转换为 HTML", "<h1" in content)
            test("主题 CSS 变量", "--bg-primary" in content)
            test("KaTeX 引入", "katex" in content.lower())
            test("Mermaid 引入", "mermaid" in content.lower())
            
            os.remove(result_path)
        else:
            test("HTML 文件生成", False, "文件不存在")
    except Exception as e:
        test("完整渲染流程", False, str(e))
    
    # 测试 4: 主题切换
    print("\n▶ 测试 4: 多主题支持")
    for style in ["dark_lab", "clean_paper", "neon_tech"]:
        try:
            r = PaperRenderer(style=style)
            test(f"{style} 主题初始化", True)
        except Exception as e:
            test(f"{style} 主题初始化", False, str(e))
    
    # 总结
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"  结果: {passed}/{total} 通过 | {'🎉 ALL PASS!' if failed == 0 else str(failed) + ' FAILED'}")
    print("=" * 60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
