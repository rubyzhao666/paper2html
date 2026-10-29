"""
解析器选择。

默认数字 PDF：Doc2X → PDF2X → PPX。
MiniCPM-OCR 只在下面两种情况进入链路：

- `auto` 且 PDF 没有可用文本层，并且已经配置了 MiniCPM 服务地址
- 显式 `--parser minicpm` / `PAPER2HTML_PARSER=minicpm`

`MINICPM_OCR_FALLBACK=1` 时，数字链路全部失败后才追加一次 MiniCPM，
不会在 Doc2X 可用时抢先调用。
"""

from __future__ import annotations

from typing import Optional

from .doc2x_parser import Doc2XParser
from .minicpm_parser import MiniCPMParser
from .pdf2x_parser import PDF2XParser
from .ppx_parser import PPXParser

PARSER_NAMES = ("auto", "doc2x", "pdf2x", "ppx", "minicpm")
DIGITAL_CHAIN = ("doc2x", "pdf2x", "ppx")

_ALIASES = {
    "mini-cpm": "minicpm",
    "minicpm-ocr": "minicpm",
    "minicpm_ocr": "minicpm",
    "ocr": "minicpm",
}


def normalize_parser_name(name: Optional[str]) -> str:
    mode = (name or "auto").strip().lower()
    mode = _ALIASES.get(mode, mode)
    if mode not in PARSER_NAMES:
        raise ValueError(
            "未知解析器: %s。可选: %s" % (name, ", ".join(PARSER_NAMES))
        )
    return mode


def build_parser_plan(
    mode: str = "auto",
    *,
    scanned: bool = False,
    minicpm_configured: bool = False,
    minicpm_fallback: bool = False,
) -> list[str]:
    """
    返回本次要依次尝试的解析器名称。

    显式的 `doc2x` / `pdf2x` / `ppx` 不因为扫描件检测插入 MiniCPM。
    显式的 `minicpm` 也不回退到付费 API。
    """
    selected = normalize_parser_name(mode)
    if selected == "doc2x":
        return list(DIGITAL_CHAIN)
    if selected == "pdf2x":
        return ["pdf2x", "ppx"]
    if selected == "ppx":
        return ["ppx"]
    if selected == "minicpm":
        return ["minicpm"]

    plan: list[str] = []
    if scanned and minicpm_configured:
        plan.append("minicpm")
    plan.extend(DIGITAL_CHAIN)
    if minicpm_fallback and minicpm_configured and "minicpm" not in plan:
        plan.append("minicpm")
    return plan


def create_parser(
    name: str,
    *,
    doc2x_api_key: Optional[str] = None,
    pdf2x_api_key: Optional[str] = None,
    minicpm_api_key: Optional[str] = None,
    minicpm_base_url: Optional[str] = None,
    minicpm_model: Optional[str] = None,
    minicpm_use_sdk: Optional[bool] = None,
):
    """按名称构造解析器。`auto` 不是具体后端。"""
    selected = normalize_parser_name(name)
    if selected == "auto":
        raise ValueError("create_parser 需要具体解析器名称，不能是 auto")
    if selected == "doc2x":
        return Doc2XParser(api_key=doc2x_api_key)
    if selected == "pdf2x":
        return PDF2XParser(api_key=pdf2x_api_key)
    if selected == "ppx":
        return PPXParser()
    return MiniCPMParser(
        api_key=minicpm_api_key,
        base_url=minicpm_base_url,
        model=minicpm_model,
        use_sdk=minicpm_use_sdk,
    )
