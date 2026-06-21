"""
Unit tests for the Hardened PDF Exporter module
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from shared.intelligence.models import ReadinessAssessment, RiskFinding, ChecklistTask
from .pdf_exporter import PdfReportGenerator, escape_pdf_text, wrap_text

class TestPdfExporter(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.generator = PdfReportGenerator(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_escape_pdf_text(self):
        self.assertEqual(escape_pdf_text("Normal text"), "Normal text")
        self.assertEqual(escape_pdf_text("App (com.example)"), "App \\(com.example\\)")
        self.assertEqual(escape_pdf_text("Backslash \\ path"), "Backslash \\\\ path")

    def test_wrap_text(self):
        long_text = "This is a very long text that needs wrapping because it exceeds character limits."
        wrapped = wrap_text(long_text, width_chars=20)
        self.assertGreater(len(wrapped), 1)
        for line in wrapped:
            self.assertLessEqual(len(line), 20)

    def test_pdf_generation_writes_valid_header_and_trailer(self):
        assessment = ReadinessAssessment(
            readiness_score=92,
            readiness_state="READY",
            verdicts={"contacts_ready": True, "sms_ready": True, "call_logs_ready": True},
            overall_assessment="Device is fully prepared.",
            findings=[],
            checklist=[
                ChecklistTask("task_1", "Step instructions", "MUST", "PRE_RESET", "COMPLETED")
            ],
            inventory=[
                {"package_name": "com.pkg", "app_name": "App", "version_name": "1.0", "allow_backup": True, "risk_score": 10}
            ]
        )
        device_summary = {
            "device_name": "Google Pixel 7 Pro",
            "model": "Pixel 7 Pro",
            "serial": "123456",
            "android_version": "14",
            "api_level": 34,
            "total_storage_bytes": 1024**3 * 10,
            "used_storage_bytes": 1024**3 * 8
        }

        out_path = self.generator.generate_report(assessment, device_summary, "test_report.pdf")
        self.assertTrue(os.path.exists(out_path))

        # Read binary file header and trailer
        with open(out_path, "rb") as f:
            pdf_data = f.read()

        self.assertTrue(pdf_data.startswith(b"%PDF-1.4"))
        self.assertTrue(pdf_data.endswith(b"%%EOF\n"))

    @patch("builtins.open")
    def test_pdf_generation_permission_error_handling(self, mock_open):
        mock_open.side_effect = PermissionError("File locked by another process")
        
        assessment = ReadinessAssessment(80, "WARNING", {}, "Overall info", [], [], [])
        device_summary = {}

        with self.assertRaises(IOError) as ctx:
            self.generator.generate_report(assessment, device_summary, "locked.pdf")

        self.assertIn("Permission denied", str(ctx.exception))
        self.assertIn("locked or inaccessible", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
