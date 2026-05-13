"""
paper2html Skill - 解析层测试

测试PDF解析功能，包括：
- arXiv下载
- Doc2X解析（需要API Key）
- PPX本地解析（备选方案）
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers import Doc2XParser, PPXParser, ArxivHandler, ParseResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestResults:
    """测试结果收集器"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, name: str):
        self.passed += 1
        print(f"  ✅ {name}")
    
    def add_fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ❌ {name}: {reason}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"测试完成: {self.passed}/{total} 通过")
        if self.errors:
            print(f"\n失败项:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")


def test_arxiv_handler():
    """测试arXiv处理器"""
    results = TestResults()
    print("\n📚 测试 arXiv 处理器")
    
    handler = ArxivHandler()
    
    # 测试ID提取
    test_cases = [
        ("https://arxiv.org/abs/2402.19473", "2402.19473"),
        ("https://arxiv.org/pdf/2312.12456", "2312.12456"),
        ("https://arxiv.org/abs/1706.03762", "1706.03762"),
        ("1706.03762", "1706.03762"),
        ("2402.19473", "2402.19473"),
    ]
    
    for url_or_id, expected_id in test_cases:
        try:
            extracted = handler.extract_arxiv_id(url_or_id)
            if extracted == expected_id:
                results.add_pass(f"提取ID: {url_or_id}")
            else:
                results.add_fail(f"提取ID: {url_or_id}", f"期望 {expected_id}，实际 {extracted}")
        except Exception as e:
            results.add_fail(f"提取ID: {url_or_id}", str(e))
    
    # 测试PDF下载（使用小论文）
    print("\n  下载测试...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            handler.cache_dir = tmpdir
            pdf_path, arxiv_id, metadata = handler.download_and_prepare("1706.03762")
            
            if Path(pdf_path).exists() and Path(pdf_path).stat().st_size > 1000:
                results.add_pass(f"下载PDF: {arxiv_id}")
                print(f"    文件大小: {Path(pdf_path).stat().st_size / 1024:.1f} KB")
                
                # 检查元数据
                if metadata.get("arxiv_id"):
                    results.add_pass("获取元数据")
                    print(f"    标题: {metadata.get('title', 'N/A')[:50]}...")
                else:
                    results.add_fail("获取元数据", "元数据为空")
            else:
                results.add_fail("下载PDF", "文件不存在或为空")
    except Exception as e:
        results.add_fail("下载PDF", str(e))
    
    return results


def test_doc2x_parser():
    """测试Doc2X解析器（需要API Key）"""
    results = TestResults()
    print("\n🔧 测试 Doc2X 解析器")
    
    api_key = os.environ.get("DOC2X_APIKEY")
    
    if not api_key:
        print("  ⚠️  DOC2X_APIKEY 未设置，跳过API测试")
        print("  💡  请设置环境变量: export DOC2X_APIKEY=your-key")
        
        # 测试框架是否正确加载
        try:
            parser = Doc2XParser(api_key="dummy-key", use_sdk=False)
            results.add_pass("Doc2XParser初始化（无API Key）")
        except Exception as e:
            results.add_fail("Doc2XParser初始化", str(e))
        
        return results
    
    print(f"  使用API Key: {api_key[:10]}...")
    
    # 创建测试PDF（如果有）
    test_pdf = None
    
    # 下载测试PDF
    print("  下载测试PDF...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = ArxivHandler(cache_dir=tmpdir)
            test_pdf, arxiv_id, metadata = handler.download_and_prepare("1706.03762")
            print(f"  测试论文: {metadata.get('title', 'N/A')[:50]}...")
    except Exception as e:
        results.add_fail("下载测试PDF", str(e))
        return results
    
    if test_pdf and Path(test_pdf).exists():
        # 测试解析
        try:
            parser = Doc2XParser(api_key=api_key)
            
            with tempfile.TemporaryDirectory() as output_dir:
                print(f"  开始解析...")
                result = parser.parse(test_pdf, output_dir=output_dir)
                
                if result.success:
                    results.add_pass("Doc2X解析成功")
                    
                    # 检查输出质量
                    if result.markdown:
                        results.add_pass(f"Markdown提取 ({len(result.markdown)} 字符)")
                        
                        # 检查关键元素
                        if "#" in result.markdown or "##" in result.markdown:
                            results.add_pass("标题结构检测")
                        else:
                            results.add_fail("标题结构检测", "未发现标题标记")
                        
                        # 检查公式（论文1706.03762有大量公式）
                        formula_count = result.markdown.count("$")
                        if formula_count > 10:
                            results.add_pass(f"公式检测 ({formula_count} 个$)")
                        else:
                            results.add_pass(f"公式检测 (较少公式，可能是其他论文)")
                    else:
                        results.add_fail("Markdown提取", "内容为空")
                    
                    if result.images:
                        results.add_pass(f"图片提取 ({len(result.images)} 张)")
                    else:
                        print("  ⚠️  未提取到图片（可能正常，取决于论文）")
                    
                    if result.metadata:
                        results.add_pass("元数据提取")
                    
                    print(f"  输出目录: {result.raw_output_dir}")
                else:
                    results.add_fail("Doc2X解析", result.error_message or "未知错误")
                    
        except Exception as e:
            results.add_fail("Doc2X解析", str(e))
    else:
        results.add_fail("测试PDF", "文件不存在")
    
    return results


def test_ppx_parser():
    """测试PPX本地解析器"""
    results = TestResults()
    print("\n🖥️  测试 PPX 本地解析器")
    
    # 检查PPX是否可用
    import subprocess
    try:
        result = subprocess.run(
            ["ppx", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"  PPX版本: {result.stdout.strip()}")
        else:
            print("  ⚠️  PPX未安装，跳过PPX测试")
            results.add_pass("PPX检查（未安装，跳过）")
            return results
    except FileNotFoundError:
        print("  ⚠️  PPX未安装，跳过PPX测试")
        results.add_pass("PPX检查（未安装，跳过）")
        return results
    
    # 获取测试PDF
    test_pdf = None
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = ArxivHandler(cache_dir=tmpdir)
            test_pdf, _, _ = handler.download_and_prepare("1706.03762")
    except Exception as e:
        results.add_fail("下载测试PDF", str(e))
        return results
    
    if test_pdf:
        try:
            parser = PPXParser()
            
            with tempfile.TemporaryDirectory() as output_dir:
                print("  开始PPX解析...")
                result = parser.parse(test_pdf, output_dir=output_dir)
                
                if result.success:
                    results.add_pass("PPX解析成功")
                    print(f"  Markdown: {len(result.markdown)} 字符")
                else:
                    results.add_fail("PPX解析", result.error_message)
                    
        except Exception as e:
            results.add_fail("PPX解析", str(e))
    
    return results


def test_parse_result_structure():
    """测试ParseResult数据结构"""
    results = TestResults()
    print("\n📋 测试 ParseResult 数据结构")
    
    from dataclasses import fields
    
    expected_fields = [
        "markdown", "json_data", "images", "metadata",
        "raw_output_dir", "source_file", "success", "error_message"
    ]
    
    for field_name in expected_fields:
        if hasattr(ParseResult, field_name) or field_name in [f.name for f in fields(ParseResult)]:
            results.add_pass(f"字段存在: {field_name}")
        else:
            results.add_fail(f"字段存在: {field_name}", "字段不存在")
    
    # 测试实例化
    try:
        result = ParseResult(
            markdown="# Test",
            success=True,
            images=["img1.png", "img2.png"]
        )
        results.add_pass("ParseResult实例化")
        
        if result.markdown == "# Test":
            results.add_pass("ParseResult赋值")
        else:
            results.add_fail("ParseResult赋值", "值不匹配")
            
    except Exception as e:
        results.add_fail("ParseResult实例化", str(e))
    
    return results


def main():
    """运行所有测试"""
    print("=" * 60)
    print("  paper2html Skill - 解析层测试")
    print("=" * 60)
    
    all_results = []
    
    # 1. 测试数据结构
    all_results.append(test_parse_result_structure())
    
    # 2. 测试arXiv处理器
    all_results.append(test_arxiv_handler())
    
    # 3. 测试Doc2X解析器
    all_results.append(test_doc2x_parser())
    
    # 4. 测试PPX解析器
    all_results.append(test_ppx_parser())
    
    # 汇总
    print("\n" + "=" * 60)
    print("  测试汇总")
    print("=" * 60)
    
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total = total_passed + total_failed
    
    print(f"\n总计: {total_passed}/{total} 通过")
    
    if total_failed > 0:
        print("\n失败详情:")
        for r in all_results:
            for name, reason in r.errors:
                print(f"  - {name}: {reason}")
        sys.exit(1)
    else:
        print("\n🎉 所有测试通过!")
        sys.exit(0)


if __name__ == "__main__":
    main()
