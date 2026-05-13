#!/usr/bin/env python3
"""
paper2html - 学术论文 → 可视化HTML阅读器

一条命令从 PDF/arXiv 链接转换为精美的 HTML 阅读器。

用法：
    python paper2html.py --input paper.pdf --output output.html
    python paper2html.py --input https://arxiv.org/abs/2402.19473 --output output.html
    python paper2html.py --input paper.pdf --style neon_tech --output output.html

作者: paper2html Team
版本: 1.0.0
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import json

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# 导入各层模块
# ============================================================================

from parsers import Doc2XParser, ArxivHandler, ParseResult
from understanding import (
    PaperUnderstanding,
    LLMClient,
    UnderstandingResult,
    KeyFindingsResult,
    StructuredExtraction,
    SectionSummary
)
from rendering import PaperRenderer, get_all_style_names

# ============================================================================
# Paper2HTML 类
# ============================================================================

class Paper2HTML:
    """
    学术论文 → 可视化HTML阅读器
    
    完整的论文转换管线：
    解析层 (Doc2X/PPX) → 理解层 (LLM摘要) → 渲染层 (HTML)
    
    使用示例:
        >>> from paper2html import Paper2HTML
        >>> converter = Paper2HTML(style="dark_lab")
        >>> output_path = converter.convert("paper.pdf", "output.html")
        
        # 或使用快捷函数
        >>> from paper2html import convert_paper
        >>> output_path = convert_paper("paper.pdf", "output.html", style="neon_tech")
    """
    
    # 支持的样式预设
    AVAILABLE_STYLES = ["dark_lab", "clean_paper", "neon_tech"]
    
    def __init__(
        self,
        style: str = "dark_lab",
        doc2x_api_key: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        llm_model: Optional[str] = None,
    ):
        """
        初始化 Paper2HTML 转换器
        
        Args:
            style: 样式预设名称，可选值：
                   - "dark_lab": 深色背景，绿色强调（默认）
                   - "clean_paper": 白色背景，学术蓝强调
                   - "neon_tech": 深紫背景，霓虹强调
            doc2x_api_key: Doc2X API密钥，默认从环境变量 DOC2X_APIKEY 读取
            llm_api_key: LLM API密钥，默认从环境变量 DEEPSEEK_API_KEY 读取
            llm_base_url: LLM API Base URL，默认 https://api.deepseek.com/v1
            llm_model: LLM模型名，默认 deepseek-chat
            
        Raises:
            ValueError: 当 style 不在支持列表中时
        """
        if style not in self.AVAILABLE_STYLES:
            raise ValueError(
                f"Unknown style: {style}. "
                f"Available styles: {self.AVAILABLE_STYLES}"
            )
        
        self.style = style
        
        # 初始化 Doc2X Parser
        self.doc2x_api_key = doc2x_api_key or os.environ.get("DOC2X_APIKEY", "")
        if not self.doc2x_api_key:
            logger.warning("DOC2X_APIKEY 未设置，解析功能可能受限")
        
        # 初始化 LLM Client
        self.llm_api_key = llm_api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.llm_base_url = llm_base_url or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.llm_model = llm_model or os.environ.get("LLM_MODEL", "deepseek-chat")
        
        self._parser = None
        self._arxiv_handler = None
        self._llm_client = None
        self._understander = None
        self._renderer = None
    
    @property
    def parser(self) -> Doc2XParser:
        """懒加载解析器"""
        if self._parser is None:
            self._parser = Doc2XParser(api_key=self.doc2x_api_key)
        return self._parser
    
    @property
    def arxiv_handler(self) -> ArxivHandler:
        """懒加载arXiv处理器"""
        if self._arxiv_handler is None:
            self._arxiv_handler = ArxivHandler()
        return self._arxiv_handler
    
    @property
    def llm_client(self) -> LLMClient:
        """懒加载LLM客户端"""
        if self._llm_client is None:
            self._llm_client = LLMClient(
                api_key=self.llm_api_key,
                base_url=self.llm_base_url,
                model=self.llm_model
            )
        return self._llm_client
    
    @property
    def understander(self) -> PaperUnderstanding:
        """懒加载论文理解器"""
        if self._understander is None:
            self._understander = PaperUnderstanding(llm_client=self.llm_client)
        return self._understander
    
    @property
    def renderer(self) -> PaperRenderer:
        """懒加载渲染器"""
        if self._renderer is None:
            self._renderer = PaperRenderer(style=self.style)
        return self._renderer
    
    def convert(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        skip_understand: bool = False,
    ) -> str:
        """
        一站式转换：PDF/arXiv → HTML
        
        Args:
            input_path: 输入文件路径（本地PDF或arXiv链接）
            output_path: 输出HTML路径，默认自动生成
            skip_understand: 是否跳过理解层（只解析+渲染，无AI摘要）
            
        Returns:
            生成的HTML文件路径
            
        Raises:
            FileNotFoundError: 当PDF文件不存在时
            ValueError: 当输入格式不支持时
            RuntimeError: 当转换失败时
        """
        logger.info(f"🚀 开始转换: {input_path}")
        logger.info(f"   样式预设: {self.style}")
        
        # Step 1: 解析
        logger.info("=" * 50)
        logger.info("📥 Step 1/3: 解析PDF...")
        parse_result = self.parse(input_path)
        
        if not parse_result.success:
            raise RuntimeError(f"解析失败: {parse_result.error_message}")
        
        logger.info(f"   ✓ 解析完成，Markdown长度: {len(parse_result.markdown)} 字符")
        
        # Step 2: 理解（可选）
        if skip_understand:
            logger.info("=" * 50)
            logger.info("⏭️ Step 2/3: 跳过理解层（--no-understand）")
            understanding_result = self._create_mock_understanding(parse_result)
        else:
            logger.info("=" * 50)
            logger.info("🤖 Step 2/3: AI理解...")
            understanding_result = self.understand(parse_result)
            
            if not understanding_result.success:
                logger.warning(f"   ⚠ 理解层部分失败: {understanding_result.error_message}")
                # 使用模拟结果继续
                understanding_result = self._create_mock_understanding(parse_result)
            else:
                logger.info(f"   ✓ 理解完成: {understanding_result.tldr[:50]}...")
        
        # 将理解层提取的标题和作者回填到metadata（解析层可能未提取到）
        if understanding_result.structured and understanding_result.structured.title:
            if not parse_result.metadata:
                parse_result.metadata = {}
            if not parse_result.metadata.get("title"):
                parse_result.metadata["title"] = understanding_result.structured.title
                logger.info(f"   ✓ 标题回填: {understanding_result.structured.title}")
            if not parse_result.metadata.get("authors") and understanding_result.structured.authors:
                parse_result.metadata["authors"] = understanding_result.structured.authors
        
        # Step 3: 渲染
        logger.info("=" * 50)
        logger.info("🎨 Step 3/3: 渲染HTML...")
        
        # 生成输出路径
        if output_path is None:
            output_path = self._generate_output_path(input_path)
        
        # 调试：渲染前确认metadata
        logger.info(f"   [DEBUG] 渲染前metadata: {parse_result.metadata}")
        
        result_path = self.render(parse_result, understanding_result, output_path)
        logger.info(f"   ✓ HTML已生成: {result_path}")
        
        logger.info("=" * 50)
        logger.info(f"✅ 转换完成！")
        logger.info(f"   输出文件: {result_path}")
        
        return result_path
    
    def parse(self, input_path: str) -> ParseResult:
        """
        解析输入文件
        
        Args:
            input_path: PDF文件路径或arXiv链接
            
        Returns:
            ParseResult 对象
        """
        # 判断输入类型
        if self._is_arxiv_url(input_path):
            return self._parse_arxiv(input_path)
        else:
            return self._parse_pdf(input_path)
    
    def understand(self, parse_result: ParseResult) -> UnderstandingResult:
        """
        理解论文内容
        
        Args:
            parse_result: ParseResult 对象
            
        Returns:
            UnderstandingResult 对象
        """
        try:
            return self.understander.understand(parse_result)
        except Exception as e:
            logger.error(f"理解失败: {e}")
            return UnderstandingResult(
                tldr="",
                key_findings=KeyFindingsResult([], "", ""),
                section_summaries=[],
                structured=StructuredExtraction("", [], "", "", "", [], [], [], "", None),
                mermaid_code="",
                success=False,
                error_message=str(e)
            )
    
    def render(
        self,
        parse_result: ParseResult,
        understanding_result: UnderstandingResult,
        output_path: str
    ) -> str:
        """
        渲染HTML
        
        Args:
            parse_result: ParseResult 对象
            understanding_result: UnderstandingResult 对象
            output_path: 输出HTML路径
            
        Returns:
            生成的HTML文件路径
        """
        return self.renderer.render(parse_result, understanding_result, output_path)
    
    # ========================================================================
    # 内部方法
    # ========================================================================
    
    def _is_arxiv_url(self, path: str) -> bool:
        """判断是否为arXiv URL"""
        if not path:
            return False
        path_lower = path.lower().strip()
        return (
            "arxiv.org" in path_lower or
            bool(self.arxiv_handler.extract_arxiv_id(path_lower))
        )
    
    def _parse_arxiv(self, url_or_id: str) -> ParseResult:
        """解析arXiv链接"""
        logger.info(f"   检测到arXiv链接，正在下载PDF...")
        
        try:
            # 下载PDF
            pdf_path, arxiv_id, metadata = self.arxiv_handler.download_and_prepare(url_or_id)
            logger.info(f"   已下载arXiv论文: {arxiv_id}")
            
            # 解析PDF
            parse_result = self.parser.parse(pdf_path)
            
            # 补充arXiv元数据
            if parse_result.success and metadata:
                if not parse_result.metadata:
                    parse_result.metadata = {}
                parse_result.metadata["arxiv_id"] = arxiv_id
                parse_result.metadata["source"] = "arxiv"
            
            return parse_result
            
        except Exception as e:
            logger.error(f"arXiv下载失败: {e}")
            return ParseResult(
                source_file=url_or_id,
                success=False,
                error_message=f"arXiv下载失败: {str(e)}"
            )
    
    def _parse_pdf(self, pdf_path: str) -> ParseResult:
        """解析本地PDF"""
        pdf_path = Path(pdf_path).resolve()
        
        if not pdf_path.exists():
            return ParseResult(
                source_file=str(pdf_path),
                success=False,
                error_message=f"PDF文件不存在: {pdf_path}"
            )
        
        if pdf_path.suffix.lower() != '.pdf':
            return ParseResult(
                source_file=str(pdf_path),
                success=False,
                error_message=f"不支持的文件格式: {pdf_path.suffix}，仅支持PDF"
            )
        
        logger.info(f"   正在解析PDF: {pdf_path.name}")
        
        try:
            parse_result = self.parser.parse(str(pdf_path))
            
            # 补充本地文件元数据
            if parse_result.success:
                if not parse_result.metadata:
                    parse_result.metadata = {}
                parse_result.metadata["source"] = "local_file"
            
            return parse_result
            
        except Exception as e:
            logger.error(f"PDF解析失败: {e}")
            return ParseResult(
                source_file=str(pdf_path),
                success=False,
                error_message=f"PDF解析失败: {str(e)}"
            )
    
    def _generate_output_path(self, input_path: str) -> str:
        """生成输出文件路径"""
        input_p = Path(input_path)
        
        # arXiv URL
        if self._is_arxiv_url(input_path):
            arxiv_id = self.arxiv_handler.extract_arxiv_id(input_path)
            if arxiv_id:
                return str(input_p.parent / f"{arxiv_id}.html")
        
        # 本地文件
        output_name = input_p.stem + ".html"
        return str(input_p.parent / output_name)
    
    def _create_mock_understanding(self, parse_result: ParseResult) -> UnderstandingResult:
        """创建模拟的理解结果（用于跳过理解层或理解失败时）"""
        # 从Markdown中提取摘要作为TL;DR
        tldr = ""
        if parse_result.markdown:
            lines = parse_result.markdown.split('\n')
            for i, line in enumerate(lines):
                if '## Abstract' in line or '## 摘要' in line:
                    # 找到下一个标题之前的内容
                    abstract_lines = []
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith('##') or lines[j].startswith('#'):
                            break
                        abstract_lines.append(lines[j].strip())
                    tldr = ' '.join(abstract_lines)[:200]
                    break
        
        return UnderstandingResult(
            tldr=tldr or "（请参考摘要部分）",
            key_findings=KeyFindingsResult(
                key_findings=[],
                innovation="",
                significance=""
            ),
            section_summaries=[],
            structured=StructuredExtraction(
                title=parse_result.metadata.get("title", "Untitled"),
                authors=parse_result.metadata.get("authors", []),
                abstract_summary=tldr,
                research_question="",
                methodology="",
                contributions=[],
                experiment_results=[],
                limitations=[],
                future_work="",
                mermaid_architecture="",
                experiment_table=None
            ),
            mermaid_code="",
            success=True
        )


# ============================================================================
# 便捷函数
# ============================================================================

def convert_paper(
    input_path: str,
    output_path: Optional[str] = None,
    style: str = "dark_lab",
    skip_understand: bool = False,
    **kwargs
) -> str:
    """
    便捷函数：一站式转换PDF/arXiv为HTML
    
    Args:
        input_path: 输入文件路径或arXiv链接
        output_path: 输出HTML路径
        style: 样式预设
        skip_understand: 跳过理解层
        **kwargs: 其他参数传递给Paper2HTML
        
    Returns:
        生成的HTML文件路径
    """
    converter = Paper2HTML(style=style, **kwargs)
    return converter.convert(input_path, output_path, skip_understand)


# ============================================================================
# CLI 入口
# ============================================================================

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        prog="paper2html",
        description="学术论文 → 可视化HTML阅读器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python paper2html.py --input paper.pdf --output output.html
  python paper2html.py --input https://arxiv.org/abs/2402.19473
  python paper2html.py --input paper.pdf --style neon_tech --output output.html
  python paper2html.py --input paper.pdf --no-understand  # 跳过AI理解

环境变量:
  DOC2X_APIKEY      Doc2X API密钥（解析用）
  DEEPSEEK_API_KEY  DeepSeek API密钥（理解用）
  DEEPSEEK_BASE_URL DeepSeek API Base URL
  LLM_MODEL         LLM模型名（默认deepseek-chat）
        """
    )
    
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="输入文件路径（本地PDF）或arXiv链接"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="输出HTML路径（默认自动生成）"
    )
    
    parser.add_argument(
        "--style", "-s",
        choices=["dark_lab", "clean_paper", "neon_tech"],
        default="dark_lab",
        help="样式预设（默认: dark_lab）"
    )
    
    parser.add_argument(
        "--api-key",
        help="Doc2X API密钥（默认从环境变量 DOC2X_APIKEY 读取）"
    )
    
    parser.add_argument(
        "--llm-api-key",
        help="LLM API密钥（默认从环境变量 DEEPSEEK_API_KEY 读取）"
    )
    
    parser.add_argument(
        "--llm-base-url",
        default="https://api.deepseek.com/v1",
        help="LLM API Base URL（默认: https://api.deepseek.com/v1）"
    )
    
    parser.add_argument(
        "--llm-model",
        default="deepseek-chat",
        help="LLM模型名（默认: deepseek-chat）"
    )
    
    parser.add_argument(
        "--no-understand",
        action="store_true",
        help="跳过理解层，只进行解析+渲染（无AI摘要）"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="开启调试模式"
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # 创建转换器
        converter = Paper2HTML(
            style=args.style,
            doc2x_api_key=args.api_key,
            llm_api_key=args.llm_api_key,
            llm_base_url=args.llm_base_url,
            llm_model=args.llm_model
        )
        
        # 执行转换
        output_path = converter.convert(
            input_path=args.input,
            output_path=args.output,
            skip_understand=args.no_understand
        )
        
        print(f"\n✅ 转换完成！")
        print(f"📄 输出文件: {output_path}")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ 文件未找到: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"\n❌ 参数错误: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"\n❌ 转换失败: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(f"\n\n⚠️ 用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n❌ 未知错误: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
