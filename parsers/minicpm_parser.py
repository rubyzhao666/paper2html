"""
MiniCPM-OCR 解析器

把扫描版或无文本层的 PDF 解析成带 `$...$` / `$$...$$` 公式的 Markdown。
数字版 PDF 的默认路径仍然是 Doc2X → PDF2X → PPX；本解析器只在显式选择
或自动检测到扫描件且已配置服务地址时使用。

支持两条路径，密钥和地址都来自参数或环境变量，不在代码里写死：

1. OpenAI 兼容接口（默认）
   - `MINICPM_API_KEY` 或 `OCR_API_KEY`
   - `MINICPM_BASE_URL` 或 `OCR_BASE_URL`（含 `/v1`）
   - 本地 vLLM / llama.cpp 也可只设 `MINICPM_SERVER_URL`
   - 可选依赖：`pymupdf`（或 `pypdfium2` / `pdf2image`）用于把 PDF 渲成图片
2. `minicpm-ocr` SDK（`MINICPM_USE_SDK=1`）
   - 调用官方 `pipelined_run` + `assemble_document_markdown`
   - 版面模型目录：`OCR_LAYOUT_MODEL_DIR` 或 `MINICPM_LAYOUT_MODEL`
   - 识别服务仍是上面的 OpenAI 兼容地址，SDK 不在这里下载主模型权重

官方说明：https://github.com/OpenBMB/MiniCPM-OCR
"""

from __future__ import annotations

import base64
import logging
import os
import re
from pathlib import Path
from typing import Any, Callable, Optional

from .models import ParseResult

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "minicpm-ocr"

# 模型按区域训练时使用短提示词。整页接口在官方提示后追加 Markdown/公式约定，
# 再把 `\[ \]` / `\( \)` 归一成 `$` 定界符，和 Doc2X/PDF2X 的 ParseResult 对齐。
PAGE_PROMPT = (
    "Text Recognition:\n"
    "Transcribe this document page into Markdown. "
    "Use $...$ for inline formulas and $$...$$ for display formulas. "
    "Keep headings, lists, and tables. Do not wrap the page in a code fence."
)

_FENCE_RE = re.compile(r"^```(?:markdown|md)?\s*\n(.*?)\n```\s*$", re.DOTALL)
_DISPLAY_RE = re.compile(r"\\\[(.*?)\\\]", re.DOTALL)
_INLINE_RE = re.compile(r"\\\((.*?)\\\)", re.DOTALL)
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _truthy(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _pick_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def resolve_minicpm_base_url(explicit: Optional[str] = None) -> str:
    """显式地址优先，否则读 MiniCPM / OCR 环境变量。"""
    if explicit is not None:
        return explicit.strip()
    return _pick_env("MINICPM_BASE_URL", "OCR_BASE_URL", "MINICPM_SERVER_URL")


def resolve_minicpm_api_key(explicit: Optional[str] = None) -> str:
    if explicit is not None:
        return explicit.strip()
    return _pick_env("MINICPM_API_KEY", "OCR_API_KEY")


def resolve_minicpm_model(explicit: Optional[str] = None) -> str:
    if explicit is not None and explicit.strip():
        return explicit.strip()
    return _pick_env("MINICPM_MODEL", "OCR_MODEL") or DEFAULT_MODEL


def minicpm_is_configured(base_url: Optional[str] = None) -> bool:
    """有服务地址才算已配置。只放了 Key、没有 URL 时不自动改解析顺序。"""
    return bool(resolve_minicpm_base_url(base_url))


def openai_base_url(url: str) -> str:
    """OpenAI SDK 需要以 `/v1` 结尾、且不含 `/chat/completions` 的 base URL。"""
    cleaned = (url or "").strip().rstrip("/")
    if cleaned.endswith("/chat/completions"):
        cleaned = cleaned[: -len("/chat/completions")].rstrip("/")
    if not cleaned.endswith("/v1"):
        cleaned = cleaned + "/v1"
    return cleaned


def sdk_server_url(url: str) -> str:
    """minicpm-ocr SDK 自己拼接 chat path，地址不要带 `/v1`。"""
    cleaned = (url or "").strip().rstrip("/")
    if cleaned.endswith("/chat/completions"):
        cleaned = cleaned[: -len("/chat/completions")].rstrip("/")
    if cleaned.endswith("/v1"):
        cleaned = cleaned[: -len("/v1")].rstrip("/")
    return cleaned


def normalize_markdown(text: str) -> str:
    """把常见公式定界符收成 `$...$` / `$$...$$`，并去掉整页代码围栏。"""
    cleaned = (text or "").strip()
    fenced = _FENCE_RE.match(cleaned)
    if fenced:
        cleaned = fenced.group(1).strip()
    cleaned = _DISPLAY_RE.sub(lambda match: "$$\n" + match.group(1).strip() + "\n$$", cleaned)
    cleaned = _INLINE_RE.sub(lambda match: "$" + match.group(1).strip() + "$", cleaned)
    return cleaned


def _message_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(str(part.get("text") or ""))
            else:
                text = getattr(part, "text", None)
                if text:
                    parts.append(str(text))
        return "\n".join(parts)
    return "" if content is None else str(content)


def _guess_title(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


class MiniCPMParser:
    """
    MiniCPM-OCR 解析器。

    `parse()` 与 Doc2X / PDF2X / PPX 相同：返回 `ParseResult`。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        use_sdk: Optional[bool] = None,
        layout_model_dir: Optional[str] = None,
        max_tokens: int = 4096,
        timeout: float = 180.0,
        zoom: float = 2.0,
        max_pages: Optional[int] = None,
        prompt: Optional[str] = None,
    ):
        self.api_key = resolve_minicpm_api_key(api_key)
        self.base_url = resolve_minicpm_base_url(base_url)
        self.model = resolve_minicpm_model(model)
        if use_sdk is None:
            self.use_sdk = _truthy(os.environ.get("MINICPM_USE_SDK"))
        else:
            self.use_sdk = bool(use_sdk)
        self.layout_model_dir = (
            layout_model_dir
            if layout_model_dir is not None
            else _pick_env("MINICPM_LAYOUT_MODEL", "OCR_LAYOUT_MODEL_DIR")
        )
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.zoom = zoom
        if max_pages is None:
            raw_pages = os.environ.get("MINICPM_MAX_PAGES", "").strip()
            try:
                self.max_pages = int(raw_pages) if raw_pages else 0
            except ValueError:
                self.max_pages = 0
        else:
            self.max_pages = max_pages
        self.prompt = prompt or PAGE_PROMPT

    @property
    def openai_base_url(self) -> str:
        return openai_base_url(self.base_url) if self.base_url else ""

    @property
    def sdk_server_url(self) -> str:
        return sdk_server_url(self.base_url) if self.base_url else ""

    def parse(self, pdf_path: str, output_dir: Optional[str] = None) -> ParseResult:
        """
        解析 PDF。

        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录，默认在 PDF 旁创建 `<stem>_minicpm`
        """
        pdf_path = Path(pdf_path).resolve()
        if not pdf_path.exists():
            return ParseResult(
                source_file=str(pdf_path),
                success=False,
                error_message=f"PDF文件不存在: {pdf_path}",
            )
        if pdf_path.suffix.lower() != ".pdf":
            return ParseResult(
                source_file=str(pdf_path),
                success=False,
                error_message=f"不支持的文件格式: {pdf_path.suffix}，仅支持PDF",
            )

        if output_dir is None:
            output_dir = pdf_path.parent / f"{pdf_path.stem}_minicpm"
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.use_sdk:
            sdk_result = self._parse_with_sdk(pdf_path, output_dir)
            if sdk_result.success and sdk_result.markdown.strip():
                return sdk_result
            logger.warning(
                "MiniCPM SDK 解析未成功(%s)，尝试 OpenAI 兼容接口",
                sdk_result.error_message or "空内容",
            )
            if not self.base_url:
                return sdk_result

        return self._parse_with_openai(pdf_path, output_dir)

    def build_sdk_overrides(self, pdf_path: Path, output_dir: Path) -> dict:
        """构造传给 `minicpmvocr.load_config` 的覆盖项。"""
        overrides: dict[str, Any] = {
            "run": {
                "run_tag": f"paper2html_{pdf_path.stem}",
                "run_root": str(output_dir / "runs"),
                "mode": "oneshot_file",
            },
            "input": {
                "file_path": str(pdf_path),
                "manifest": "",
                "image_dir": "",
                "files_dir": "",
                "limit": 0,
            },
            "engine": {
                "type": "openai",
                "server_url": self.sdk_server_url,
                "model_name": self.model,
                "api_key": self.api_key,
                "max_model_len": 40960,
            },
        }
        layout: dict[str, Any] = {}
        if self.layout_model_dir:
            layout["model_dir"] = self.layout_model_dir
        device = _pick_env("OCR_LAYOUT_DEVICE", "MINICPM_LAYOUT_DEVICE")
        if device:
            layout["device"] = device
        if layout:
            overrides["layout"] = layout
        return overrides

    def _parse_with_sdk(self, pdf_path: Path, output_dir: Path) -> ParseResult:
        if not self.sdk_server_url:
            return self._failure(
                pdf_path,
                "MiniCPM SDK 需要识别服务地址。请设置 MINICPM_BASE_URL 或 MINICPM_SERVER_URL。",
            )
        try:
            from importlib.resources import files

            from minicpmvocr import (
                assemble_document_markdown,
                load_config,
                load_prompt_map,
                pipelined_run,
            )
        except ImportError as exc:
            return self._failure(
                pdf_path,
                "未安装 minicpm-ocr SDK (%s)。请运行 pip install 'minicpm-ocr[pdf]'，"
                "或取消 MINICPM_USE_SDK，改用 OpenAI 兼容接口。" % exc,
            )

        try:
            config_path = files("minicpmvocr").joinpath("configs/minicpmvocr.yaml")
            cfg = load_config(str(config_path), overrides=self.build_sdk_overrides(pdf_path, output_dir))
            pipelined_run(cfg)
            markdown, page_count, merge_count = assemble_document_markdown(
                Path(cfg["_meta"]["run_dir"]),
                load_prompt_map(cfg),
                merge_tables=bool((cfg.get("pipeline") or {}).get("merge_cross_page_tables", False)),
                delimiter="\n\n",
            )
        except Exception as exc:
            return self._failure(pdf_path, "MiniCPM SDK 解析失败: %s" % exc)

        markdown = normalize_markdown(markdown or "")
        if not markdown.strip():
            return self._failure(pdf_path, "MiniCPM SDK 返回空内容")

        run_dir = Path(cfg["_meta"]["run_dir"])
        images = [
            str(path)
            for path in run_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES
        ]
        metadata = {
            "parser": "minicpm",
            "backend": "sdk",
            "model": self.model,
            "page_count": page_count,
            "cross_page_merges": merge_count,
            "output_dir": str(output_dir),
        }
        title = _guess_title(markdown)
        if title:
            metadata["title"] = title
        return ParseResult(
            markdown=markdown,
            json_data={"backend": "sdk", "page_count": page_count},
            images=images,
            metadata=metadata,
            raw_output_dir=str(run_dir),
            source_file=str(pdf_path),
            success=True,
        )

    def _parse_with_openai(self, pdf_path: Path, output_dir: Path) -> ParseResult:
        if not self.base_url:
            return self._failure(pdf_path, self._missing_endpoint_message())

        try:
            image_paths = self._render_pages(pdf_path, output_dir / "pages")
        except Exception as exc:
            return self._failure(pdf_path, str(exc))

        truncated = False
        if self.max_pages and len(image_paths) > self.max_pages:
            image_paths = image_paths[: self.max_pages]
            truncated = True

        try:
            client = self._make_client()
        except Exception as exc:
            return self._failure(pdf_path, "无法创建 OpenAI 客户端: %s" % exc)

        parts = []
        records = []
        for index, image_path in enumerate(image_paths, start=1):
            try:
                text, finish_reason = self._recognize_image(client, image_path)
            except Exception as exc:
                return self._failure(pdf_path, "MiniCPM 第 %s 页识别失败: %s" % (index, exc))
            text = normalize_markdown(text)
            parts.append(text)
            records.append(
                {
                    "page": index,
                    "finish_reason": finish_reason,
                    "chars": len(text),
                }
            )

        markdown = "\n\n".join(part for part in parts if part.strip()).strip()
        if not markdown:
            return self._failure(pdf_path, "MiniCPM 返回空内容")

        metadata = {
            "parser": "minicpm",
            "backend": "openai",
            "model": self.model,
            "page_count": len(image_paths),
            "truncated": truncated,
            "output_dir": str(output_dir),
        }
        title = _guess_title(markdown)
        if title:
            metadata["title"] = title
        return ParseResult(
            markdown=markdown,
            json_data={"backend": "openai", "pages": records},
            images=[str(path) for path in image_paths],
            metadata=metadata,
            raw_output_dir=str(output_dir),
            source_file=str(pdf_path),
            success=True,
        )

    def _make_client(self):
        from openai import OpenAI

        return OpenAI(
            api_key=self.api_key or "EMPTY",
            base_url=self.openai_base_url,
            timeout=self.timeout,
        )

    def _recognize_image(self, client, image_path: Path) -> tuple[str, Optional[str]]:
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        suffix = image_path.suffix.lower().lstrip(".") or "png"
        mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else "image/%s" % suffix
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:%s;base64,%s" % (mime, encoded)},
                        },
                        {"type": "text", "text": self.prompt},
                    ],
                }
            ],
            temperature=0.01,
            top_p=0.001,
            max_tokens=self.max_tokens,
        )
        choice = response.choices[0]
        return _message_text(choice.message), getattr(choice, "finish_reason", None)

    def _render_pages(self, pdf_path: Path, image_dir: Path) -> list[Path]:
        image_dir.mkdir(parents=True, exist_ok=True)
        renderers: list[tuple[str, Callable[[Path, Path, float], list[Path]]]] = [
            ("pymupdf", _render_with_pymupdf),
            ("pypdfium2", _render_with_pypdfium2),
            ("pdf2image", _render_with_pdf2image),
        ]
        missing = []
        last_error = ""
        for name, renderer in renderers:
            try:
                pages = renderer(pdf_path, image_dir, self.zoom)
            except ImportError:
                missing.append(name)
                continue
            except Exception as exc:
                last_error = "%s: %s" % (name, exc)
                logger.warning("使用 %s 渲染 PDF 失败: %s", name, exc)
                continue
            if pages:
                return pages
            last_error = "%s 没有渲染出页面" % name
        hint = (
            "MiniCPM 整页 OCR 需要把 PDF 渲染成图片。请安装其一: pip install pymupdf"
            "（也可使用 pypdfium2，或 pdf2image 加 poppler）。"
            "若已安装 minicpm-ocr 并准备好版面模型，可设置 MINICPM_USE_SDK=1。"
        )
        if last_error:
            hint = "%s 渲染失败（%s）。%s" % (pdf_path.name, last_error, hint)
        elif missing:
            hint = "%s %s" % (hint, "未安装: " + ", ".join(missing))
        raise RuntimeError(hint)

    def _failure(self, pdf_path: Path, message: str) -> ParseResult:
        return ParseResult(
            source_file=str(pdf_path),
            success=False,
            error_message=self._redact(message),
            metadata={"parser": "minicpm", "model": self.model},
        )

    def _redact(self, message: str) -> str:
        if self.api_key and self.api_key in message:
            return message.replace(self.api_key, "***")
        return message

    @staticmethod
    def _missing_endpoint_message() -> str:
        return (
            "MiniCPM 未配置服务地址。请设置 MINICPM_BASE_URL（或 OCR_BASE_URL），"
            "以及托管服务的 MINICPM_API_KEY（或 OCR_API_KEY）。"
            "本地推理可设置 MINICPM_SERVER_URL=http://127.0.0.1:18499 "
            "和 MINICPM_MODEL=minicpm-ocr，无需把密钥写进代码。"
        )


def _render_with_pymupdf(pdf_path: Path, image_dir: Path, zoom: float) -> list[Path]:
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz

    document = fitz.open(pdf_path)
    paths = []
    try:
        matrix = fitz.Matrix(zoom, zoom)
        for index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            dest = image_dir / ("page_%04d.png" % index)
            pixmap.save(str(dest))
            paths.append(dest)
    finally:
        document.close()
    return paths


def _render_with_pypdfium2(pdf_path: Path, image_dir: Path, zoom: float) -> list[Path]:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(pdf_path))
    paths = []
    try:
        scale = zoom
        for index in range(len(document)):
            page = document[index]
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil()
            dest = image_dir / ("page_%04d.png" % (index + 1))
            image.save(dest, format="PNG")
            paths.append(dest)
            page.close()
    finally:
        document.close()
    return paths


def _render_with_pdf2image(pdf_path: Path, image_dir: Path, zoom: float) -> list[Path]:
    from pdf2image import convert_from_path

    images = convert_from_path(str(pdf_path), dpi=max(72, int(72 * zoom)))
    paths = []
    for index, image in enumerate(images, start=1):
        dest = image_dir / ("page_%04d.png" % index)
        image.save(dest, format="PNG")
        paths.append(dest)
    return paths


def parse_pdf_minicpm(pdf_path: str, **kwargs) -> ParseResult:
    """便捷函数：使用 MiniCPM-OCR 解析 PDF。"""
    return MiniCPMParser(**kwargs).parse(pdf_path)
