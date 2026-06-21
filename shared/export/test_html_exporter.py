"""
Unit tests for the HTML Report Exporter module
"""

import os
import tempfile
import unittest
from shared.intelligence.models import ReadinessAssessment, RiskFinding, ChecklistTask
from .html_exporter import HtmlReportEngine, TemplateRenderer

class TestHtmlExporter(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_template_renderer_placeholders(self):
        template = "Model: {{ device.model }} API: {{ device.api }}"
        context = {"device": {"model": "Pixel 7 Pro", "api": 33}}
        result = TemplateRenderer.render(template, context)
        self.assertEqual(result, "Model: Pixel 7 Pro API: 33")

    def test_template_renderer_conditionals(self):
        template = "{% if val %}YES{% else %}NO{% endif %}"
        self.assertEqual(TemplateRenderer.render(template, {"val": True}), "YES")
        self.assertEqual(TemplateRenderer.render(template, {"val": False}), "NO")

        # Test value comparison equality check
        template_eq = "{% if state == 'READY' %}GO{% else %}STOP{% endif %}"
        self.assertEqual(TemplateRenderer.render(template_eq, {"state": "READY"}), "GO")
        self.assertEqual(TemplateRenderer.render(template_eq, {"state": "WARNING"}), "STOP")

    def test_template_renderer_loops(self):
        template = "{% for item in items %}{{ item.name }}-{% endfor %}"
        context = {"items": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}
        result = TemplateRenderer.render(template, context)
        self.assertEqual(result, "A-B-C-")

    def test_template_renderer_filters(self):
        template = "Name: {{ name | lower }} Size: {{ size | filesizeformat }}"
        context = {"name": "PHOENIX", "size": 1024 * 1024 * 5}
        result = TemplateRenderer.render(template, context)
        self.assertEqual(result, "Name: phoenix Size: 5.0 MB")

    def test_html_report_generation(self):
        assessment = ReadinessAssessment(
            readiness_score=85,
            readiness_state="WARNING",
            verdicts={"contacts_ready": True, "sms_ready": False, "call_logs_ready": True},
            overall_assessment="Baseline backups verified, but SMS data requires attention.",
            findings=[
                RiskFinding(
                    package_name="org.thoughtcrime.securesms",
                    app_name="Signal",
                    category="SECURE_MESSENGER",
                    severity="HIGH",
                    reasoning="Local SQLCipher DB settings.",
                    remediation="Enable Signal chat backups."
                )
            ],
            checklist=[
                ChecklistTask(
                    task_id="task_signal",
                    step="Enable Signal chat backups.",
                    priority="SHOULD",
                    timing="PRE_RESET",
                    status="PENDING"
                )
            ],
            inventory=[
                {
                    "package_name": "org.thoughtcrime.securesms",
                    "app_name": "Signal",
                    "version_name": "6.40.4",
                    "allow_backup": False,
                    "risk_score": 75
                }
            ]
        )

        device_summary = {
            "device_name": "Google Pixel 7 Pro",
            "model": "Pixel 7 Pro",
            "serial": "12345",
            "android_version": "13",
            "api_level": 33,
            "total_storage_bytes": 128 * 1024 * 1024 * 1024,
            "used_storage_bytes": 100 * 1024 * 1024 * 1024
        }

        output_path = os.path.join(self.test_dir.name, "readiness_report.html")
        engine = HtmlReportEngine()
        
        # Add a custom future report section (extensibility requirement)
        additional_sections = [
            {
                "title": "Cloud Backup Statistics",
                "content_html": "<p>Google One sync status is <strong>Active</strong>.</p>"
            }
        ]

        html_content = engine.generate_report(
            assessment=assessment,
            device_summary=device_summary,
            output_path=output_path,
            additional_sections=additional_sections
        )

        self.assertTrue(os.path.exists(output_path))
        
        # Verify rendered elements
        self.assertIn("Phoenix Recovery Readiness Report", html_content)
        self.assertIn("Pixel 7 Pro", html_content)
        self.assertIn("85", html_content)
        self.assertIn("WARNING", html_content)
        self.assertIn("Signal", html_content)
        self.assertIn("Enable Signal chat backups.", html_content)
        self.assertIn("Cloud Backup Statistics", html_content)
        self.assertIn("Google One sync status", html_content)

if __name__ == "__main__":
    unittest.main()
