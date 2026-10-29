"""MiniCPM 解析器与解析顺序测试。不访问真实 OCR 服务。"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers import (
    Doc2XParser,
    MiniCPMParser,
    PDF2XParser,
    PPXParser,
    ParseResult,
    build_parser_plan,
    create_parser,
)
from parsers.minicpm_parser import (
    normalize_markdown,
    openai_base_url,
    sdk_server_url,
)
from parsers.pdf_probe import pdf_lacks_text_layer


TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
    b"\x00\x05\xfe\x02\xfe\xa7\x9a\x8c\x00\x00\x00\x00IEND\xaeB`\x82"
)


class PlanTests(unittest.TestCase):
    def test_auto_digital_prefers_doc2x_even_if_minicpm_configured(self):
        plan = build_parser_plan("auto", scanned=False, minicpm_configured=True)
        self.assertEqual(plan, ["doc2x", "pdf2x", "ppx"])

    def test_auto_scanned_uses_minicpm_only_when_configured(self):
        self.assertEqual(
            build_parser_plan("auto", scanned=True, minicpm_configured=True),
            ["minicpm", "doc2x", "pdf2x", "ppx"],
        )
        self.assertEqual(
            build_parser_plan("auto", scanned=True, minicpm_configured=False),
            ["doc2x", "pdf2x", "ppx"],
        )

    def test_explicit_modes_do_not_mix_chains(self):
        self.assertEqual(build_parser_plan("doc2x", scanned=True, minicpm_configured=True), ["doc2x", "pdf2x", "ppx"])
        self.assertEqual(build_parser_plan("minicpm", scanned=False), ["minicpm"])
        self.assertEqual(build_parser_plan("minicpm-ocr"), ["minicpm"])
        self.assertEqual(build_parser_plan("ppx"), ["ppx"])

    def test_fallback_appends_minicpm_after_digital_failure_slot(self):
        plan = build_parser_plan(
            "auto",
            scanned=False,
            minicpm_configured=True,
            minicpm_fallback=True,
        )
        self.assertEqual(plan, ["doc2x", "pdf2x", "ppx", "minicpm"])

    def test_unknown_parser_rejected(self):
        with self.assertRaises(ValueError):
            build_parser_plan("paddle")
        with self.assertRaises(ValueError):
            create_parser("auto")


class FormulaTests(unittest.TestCase):
    def test_bracket_delimiters_become_dollar_math(self):
        text = normalize_markdown("Energy \\[E = mc^2\\] and inline \\(a+b\\).")
        self.assertIn("$$\nE = mc^2\n$$", text)
        self.assertIn("$a+b$", text)
        self.assertNotIn(r"\[", text)
        self.assertNotIn(r"\(", text)

    def test_existing_dollars_and_code_fence(self):
        raw = "```markdown\nKeep $x$ and $$y$$\n```"
        self.assertEqual(normalize_markdown(raw), "Keep $x$ and $$y$$")


class EndpointTests(unittest.TestCase):
    def test_url_shapes(self):
        self.assertEqual(openai_base_url("http://127.0.0.1:18499"), "http://127.0.0.1:18499/v1")
        self.assertEqual(openai_base_url("http://127.0.0.1:18499/v1/"), "http://127.0.0.1:18499/v1")
        self.assertEqual(sdk_server_url("https://ocr.example/v1"), "https://ocr.example")

    def test_sdk_overrides_keep_key_out_of_model_path(self):
        parser = MiniCPMParser(
            api_key="secret-key",
            base_url="http://127.0.0.1:18499/v1",
            model="minicpm-ocr",
            use_sdk=True,
            layout_model_dir="/models/PP-DocLayoutV3",
        )
        overrides = parser.build_sdk_overrides(Path("/tmp/paper.pdf"), Path("/tmp/out"))
        self.assertEqual(overrides["engine"]["type"], "openai")
        self.assertEqual(overrides["engine"]["server_url"], "http://127.0.0.1:18499")
        self.assertEqual(overrides["engine"]["api_key"], "secret-key")
        self.assertEqual(overrides["engine"]["model_name"], "minicpm-ocr")
        self.assertEqual(overrides["layout"]["model_dir"], "/models/PP-DocLayoutV3")
        self.assertNotIn("secret-key", overrides["engine"]["server_url"])

    def test_error_redacts_api_key(self):
        parser = MiniCPMParser(api_key="secret-key", base_url="http://127.0.0.1:9/v1")
        result = parser._failure(Path("a.pdf"), "rejected secret-key")
        self.assertNotIn("secret-key", result.error_message)
        self.assertIn("***", result.error_message)


class ParseContractTests(unittest.TestCase):
    def test_missing_endpoint_does_not_call_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "scan.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            with mock.patch.dict(os.environ, {}, clear=False):
                for name in (
                    "MINICPM_BASE_URL",
                    "OCR_BASE_URL",
                    "MINICPM_SERVER_URL",
                    "MINICPM_API_KEY",
                    "OCR_API_KEY",
                    "MINICPM_USE_SDK",
                ):
                    os.environ.pop(name, None)
                parser = MiniCPMParser(use_sdk=False)
                result = parser.parse(str(pdf_path))
        self.assertFalse(result.success)
        self.assertIn("MINICPM_BASE_URL", result.error_message)
        self.assertEqual(result.markdown, "")

    def test_openai_path_returns_parse_result(self):
        captured = {}

        class FakeCompletions:
            def create(self, **kwargs):
                captured["request"] = kwargs
                message = SimpleNamespace(
                    content="# Scanned Title\n\nEnergy \\[E = mc^2\\]\n\ninline \\(a+b\\).",
                    finish_reason="stop",
                )
                return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")])

        class FakeClient:
            def __init__(self):
                self.chat = SimpleNamespace(completions=FakeCompletions())

        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "scan.pdf"
            try:
                import pymupdf

                document = pymupdf.open()
                document.new_page()
                document.save(pdf_path)
                document.close()
            except ImportError:
                pdf_path.write_bytes(b"%PDF-1.4\n")
            parser = MiniCPMParser(
                api_key="secret-key",
                base_url="http://ocr.example/v1",
                model="minicpm-ocr",
                use_sdk=False,
            )
            if not pdf_path.read_bytes().startswith(b"%PDF"):
                self.fail("fixture pdf was not written")

            def render(pdf, image_dir):
                image_dir = Path(image_dir)
                image_dir.mkdir(parents=True, exist_ok=True)
                dest = image_dir / "page_0001.png"
                dest.write_bytes(TINY_PNG)
                captured["rendered"] = str(pdf)
                return [dest]

            # Prefer the real renderer when PyMuPDF can open the fixture.
            try:
                import pymupdf  # noqa: F401

                probe = parser._render_pages(pdf_path, Path(tmp) / "probe-pages")
                self.assertTrue(probe and probe[0].is_file())
            except Exception:
                parser._render_pages = render
            parser._make_client = lambda: FakeClient()
            result = parser.parse(str(pdf_path), output_dir=str(Path(tmp) / "out"))

        self.assertTrue(result.success, result.error_message)
        self.assertIn("$$\nE = mc^2\n$$", result.markdown)
        self.assertIn("$a+b$", result.markdown)
        self.assertTrue(result.images)
        self.assertEqual(result.metadata["parser"], "minicpm")
        self.assertEqual(result.metadata["backend"], "openai")
        self.assertEqual(result.metadata["title"], "Scanned Title")
        self.assertEqual(captured["request"]["model"], "minicpm-ocr")
        self.assertIn("Text Recognition:", captured["request"]["messages"][0]["content"][1]["text"])
        self.assertTrue(captured["request"]["messages"][0]["content"][0]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertNotIn("secret-key", result.markdown)

    def test_sdk_success_skips_openai(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "scan.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            parser = MiniCPMParser(api_key="k", base_url="http://ocr.example/v1", use_sdk=True)
            parser._parse_with_sdk = lambda *args, **kwargs: ParseResult(
                markdown="SDK $$x$$",
                success=True,
                metadata={"backend": "sdk", "parser": "minicpm"},
            )
            parser._parse_with_openai = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("openai called"))
            result = parser.parse(str(pdf_path))
        self.assertTrue(result.success)
        self.assertEqual(result.metadata["backend"], "sdk")

    def test_sdk_failure_falls_back_to_openai_helper(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "scan.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")
            parser = MiniCPMParser(api_key="k", base_url="http://ocr.example/v1", use_sdk=True)
            parser._parse_with_sdk = lambda *args, **kwargs: ParseResult(
                success=False,
                error_message="layout model missing",
            )
            parser._parse_with_openai = lambda *args, **kwargs: ParseResult(
                markdown="page $z$",
                success=True,
                metadata={"backend": "openai"},
            )
            result = parser.parse(str(pdf_path))
        self.assertTrue(result.success)
        self.assertEqual(result.markdown, "page $z$")


class ProbeTests(unittest.TestCase):
    def test_blank_pdf_lacks_text_and_text_pdf_does_not(self):
        try:
            import pymupdf
        except ImportError:
            self.skipTest("pymupdf is not installed")
        try:
            import PyPDF2  # noqa: F401
        except ImportError:
            self.skipTest("PyPDF2 is not installed")

        with tempfile.TemporaryDirectory() as tmp:
            blank = Path(tmp) / "blank.pdf"
            digital = Path(tmp) / "digital.pdf"
            empty = pymupdf.open()
            empty.new_page()
            empty.save(blank)
            empty.close()
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((72, 72), "This digital paper has a real text layer. " * 30)
            doc.save(digital)
            doc.close()
            self.assertTrue(pdf_lacks_text_layer(blank, min_chars_per_page=40))
            self.assertFalse(pdf_lacks_text_layer(digital, min_chars_per_page=40))


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self._env = mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()
        for name in (
            "PAPER2HTML_PARSER",
            "MINICPM_BASE_URL",
            "OCR_BASE_URL",
            "MINICPM_SERVER_URL",
            "MINICPM_API_KEY",
            "OCR_API_KEY",
            "MINICPM_OCR_FALLBACK",
            "MINICPM_USE_SDK",
            "DOC2X_APIKEY",
            "PDF2X_APIKEY",
        ):
            os.environ.pop(name, None)
        self.calls = []

        def record(name):
            def _parse(parser, pdf_path, output_dir=None):
                self.calls.append(name)
                if name == "doc2x":
                    return ParseResult(markdown="# Digital\n\n$x$", success=True, source_file=pdf_path)
                return ParseResult(success=False, error_message="%s failed" % name, source_file=pdf_path)
            return _parse

        self.patches = [
            mock.patch.object(Doc2XParser, "parse", record("doc2x")),
            mock.patch.object(PDF2XParser, "parse", record("pdf2x")),
            mock.patch.object(PPXParser, "parse", record("ppx")),
            mock.patch.object(MiniCPMParser, "parse", record("minicpm")),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in self.patches:
            patcher.stop()
        self._env.stop()

    def _pdf(self, directory):
        path = Path(directory) / "paper.pdf"
        path.write_bytes(b"%PDF-1.4\n")
        return path

    def test_digital_auto_does_not_call_minicpm(self):
        from paper2html import Paper2HTML

        os.environ["MINICPM_BASE_URL"] = "http://ocr.example/v1"
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = self._pdf(tmp)
            with mock.patch("paper2html.pdf_lacks_text_layer", return_value=False):
                result = Paper2HTML().parse(str(pdf_path))
        self.assertEqual(self.calls, ["doc2x"])
        self.assertTrue(result.success)
        self.assertEqual(result.metadata.get("parser"), "doc2x")
        self.assertEqual(result.metadata.get("source"), "local_file")
        self.assertIn("$x$", result.markdown)

    def test_scanned_auto_prefers_minicpm_when_configured(self):
        from paper2html import Paper2HTML

        os.environ["MINICPM_BASE_URL"] = "http://ocr.example/v1"

        def minicpm_ok(parser, pdf_path, output_dir=None):
            self.calls.append("minicpm")
            return ParseResult(markdown="scan $a$", success=True, source_file=pdf_path, metadata={"backend": "openai"})

        with mock.patch.object(MiniCPMParser, "parse", minicpm_ok):
            with tempfile.TemporaryDirectory() as tmp:
                pdf_path = self._pdf(tmp)
                with mock.patch("paper2html.pdf_lacks_text_layer", return_value=True):
                    result = Paper2HTML().parse(str(pdf_path))
        self.assertEqual(self.calls, ["minicpm"])
        self.assertIn("$a$", result.markdown)
        self.assertEqual(result.metadata.get("parser"), "minicpm")

    def test_explicit_minicpm_does_not_fall_back_to_doc2x(self):
        from paper2html import Paper2HTML

        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = self._pdf(tmp)
            with mock.patch("paper2html.pdf_lacks_text_layer", return_value=False):
                result = Paper2HTML(parser="minicpm", minicpm_base_url="http://ocr.example/v1").parse(str(pdf_path))
        self.assertEqual(self.calls, ["minicpm"])
        self.assertFalse(result.success)

    def test_explicit_doc2x_on_scan_stays_on_digital_chain(self):
        from paper2html import Paper2HTML

        os.environ["MINICPM_BASE_URL"] = "http://ocr.example/v1"
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = self._pdf(tmp)
            with mock.patch("paper2html.pdf_lacks_text_layer", return_value=True):
                result = Paper2HTML(parser="doc2x").parse(str(pdf_path))
        self.assertEqual(self.calls, ["doc2x"])
        self.assertTrue(result.success)

    def test_fallback_flag_runs_minicpm_only_after_digital_chain_fails(self):
        from paper2html import Paper2HTML

        os.environ["MINICPM_BASE_URL"] = "http://ocr.example/v1"
        os.environ["MINICPM_OCR_FALLBACK"] = "1"

        def fail(name):
            def _parse(parser, pdf_path, output_dir=None):
                self.calls.append(name)
                if name == "minicpm":
                    return ParseResult(markdown="ocr $b$", success=True, source_file=pdf_path)
                return ParseResult(success=False, error_message="nope", source_file=pdf_path)
            return _parse

        with mock.patch.object(Doc2XParser, "parse", fail("doc2x")), \
             mock.patch.object(PDF2XParser, "parse", fail("pdf2x")), \
             mock.patch.object(PPXParser, "parse", fail("ppx")), \
             mock.patch.object(MiniCPMParser, "parse", fail("minicpm")):
            with tempfile.TemporaryDirectory() as tmp:
                pdf_path = self._pdf(tmp)
                with mock.patch("paper2html.pdf_lacks_text_layer", return_value=False):
                    result = Paper2HTML().parse(str(pdf_path))
        self.assertEqual(self.calls, ["doc2x", "pdf2x", "ppx", "minicpm"])
        self.assertTrue(result.success)
        self.assertIn("$b$", result.markdown)


if __name__ == "__main__":
    unittest.main()
