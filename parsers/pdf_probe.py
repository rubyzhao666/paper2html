"""
检测 PDF 是否缺少可用文本层。

数字版论文通常能抽出足够多的字符；扫描件或纯图片 PDF 抽出来接近空白。
检测失败时按数字 PDF 处理，避免误把 Doc2X/PDF2X 路径换成 OCR。
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_WHITESPACE = re.compile(r"\s+")


def pdf_lacks_text_layer(
    pdf_path: str,
    *,
    min_chars_per_page: int | None = None,
    sample_pages: int = 8,
) -> bool:
    """
    抽样前几页的可提取文本。

    平均每页非空白字符少过阈值时，视为扫描件 / 无可用文本层。
    PyPDF2 缺失或读取失败时返回 False。
    """
    path = Path(pdf_path)
    if not path.is_file():
        return False

    if min_chars_per_page is None:
        raw = os.environ.get("MINICPM_SCAN_MIN_CHARS", "").strip()
        try:
            min_chars_per_page = int(raw) if raw else 40
        except ValueError:
            min_chars_per_page = 40

    try:
        import PyPDF2
    except ImportError:
        logger.debug("PyPDF2 未安装，跳过扫描件检测，按数字 PDF 处理")
        return False

    try:
        with path.open("rb") as handle:
            reader = PyPDF2.PdfReader(handle)
            if getattr(reader, "is_encrypted", False):
                try:
                    reader.decrypt("")
                except Exception:
                    logger.debug("加密 PDF 无法抽样文本，按数字 PDF 处理")
                    return False
            total = len(reader.pages)
            if total <= 0:
                return False
            checked = min(total, max(1, sample_pages))
            chars = 0
            for index in range(checked):
                text = reader.pages[index].extract_text() or ""
                chars += len(_WHITESPACE.sub("", text))
    except Exception as exc:
        logger.debug("扫描件检测失败，按数字 PDF 处理: %s", exc)
        return False

    return (chars / checked) < min_chars_per_page
