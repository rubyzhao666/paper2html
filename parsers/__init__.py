"""
paper2html Skill - 解析层
将学术论文PDF转化为结构化数据
"""

from .models import ParseResult, UnderstandingResult, LLMResponse
from .doc2x_parser import Doc2XParser
from .ppx_parser import PPXParser
from .arxiv_handler import ArxivHandler

__all__ = [
    "ParseResult",
    "UnderstandingResult", 
    "LLMResponse",
    "Doc2XParser",
    "PPXParser",
    "ArxivHandler",
]

__version__ = "1.0.0"
