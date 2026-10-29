"""
paper2html Skill - 解析层
将学术论文PDF转化为结构化数据
"""

from .models import ParseResult, UnderstandingResult, LLMResponse
from .doc2x_parser import Doc2XParser
from .pdf2x_parser import PDF2XParser
from .ppx_parser import PPXParser
from .minicpm_parser import MiniCPMParser, minicpm_is_configured
from .pdf_probe import pdf_lacks_text_layer
from .arxiv_handler import ArxivHandler
from .selector import PARSER_NAMES, build_parser_plan, create_parser, normalize_parser_name

__all__ = [
    "ParseResult",
    "UnderstandingResult", 
    "LLMResponse",
    "Doc2XParser",
    "PDF2XParser",
    "PPXParser",
    "MiniCPMParser",
    "ArxivHandler",
    "PARSER_NAMES",
    "build_parser_plan",
    "create_parser",
    "normalize_parser_name",
    "pdf_lacks_text_layer",
    "minicpm_is_configured",
]

__version__ = "1.0.0"
