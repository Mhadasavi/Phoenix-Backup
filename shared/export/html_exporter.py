"""
Phoenix Backup HTML Report Engine (Hardened Python Implementation)
"""

import os
import re
import datetime
import logging
from typing import List, Dict, Any, Optional
from shared.intelligence.models import ReadinessAssessment

logger = logging.getLogger("phoenix.export.html")

class TemplateRenderer:
    """
    Lightweight, dependency-free HTML template rendering engine.
    Supports basic variable interpolation, dot notation, simple conditionals, loops, and filters.
    """

    @staticmethod
    def render(template_str: str, context: Dict[str, Any]) -> str:
        def resolve_val(expr: str, ctx: Dict[str, Any]) -> Any:
            parts = expr.strip().split('.')
            val = ctx
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p, "")
                else:
                    val = getattr(val, p, "")
            return val

        def render_loops(html: str, ctx: Dict[str, Any]) -> str:
            pattern = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+([^%]+)\s*%\}(.*?)\{%\s*endfor\s*\%}', re.DOTALL)
            while True:
                match = pattern.search(html)
                if not match:
                    break
                item_var, list_expr, loop_content = match.groups()
                items = resolve_val(list_expr, ctx) or []
                
                loop_rendered = []
                for item in items:
                    local_ctx = ctx.copy()
                    local_ctx[item_var] = item
                    rendered_item = TemplateRenderer.render(loop_content, local_ctx)
                    loop_rendered.append(rendered_item)
                
                replacement = "".join(loop_rendered)
                html = html[:match.start()] + replacement + html[match.end():]
            return html

        def render_ifs(html: str, ctx: Dict[str, Any]) -> str:
            pattern = re.compile(r'\{%\s*if\s+([^%]+)\s*%\}(.*?)(?:\{%\s*else\s*%\}(.*?))?\{%\s*endif\s*\%}', re.DOTALL)
            while True:
                match = pattern.search(html)
                if not match:
                    break
                expr, true_content, false_content = match.groups()
                false_content = false_content or ""
                expr = expr.strip()
                result = False
                
                if expr.startswith("not "):
                    result = not bool(resolve_val(expr[4:], ctx))
                else:
                    if "==" in expr:
                        left, right = expr.split("==", 1)
                        left_val = resolve_val(left.strip(), ctx)
                        right_val = right.strip().strip('"').strip("'")
                        result = str(left_val) == right_val
                    else:
                        result = bool(resolve_val(expr, ctx))
                
                replacement = true_content if result else false_content
                html = html[:match.start()] + replacement + html[match.end():]
            return html

        # Parse loops and conditionals
        rendered = render_loops(template_str, context)
        rendered = render_ifs(rendered, context)

        # Parse double-brace variable placeholders
        placeholder_pattern = re.compile(r'\{\{\s*([^}]+)\s*\}\}')
        while True:
            match = placeholder_pattern.search(rendered)
            if not match:
                break
            expr = match.group(1).strip()
            filter_name = None
            if '|' in expr:
                expr, filter_name = expr.split('|', 1)
                expr = expr.strip()
                filter_name = filter_name.strip()
            
            val = resolve_val(expr, context)
            
            if filter_name == "lower":
                val = str(val).lower()
            elif filter_name == "filesizeformat":
                try:
                    num = float(val)
                    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                        if num < 1024.0:
                            val = f"{num:.1f} {unit}" if unit != 'B' else f"{int(num)} {unit}"
                            break
                        num /= 1024.0
                except (ValueError, TypeError):
                    pass
            
            rendered = rendered[:match.start()] + str(val) + rendered[match.end():]
            
        return rendered


DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Phoenix Recovery Readiness Report - {{ device_summary.model }}</title>
  <style>
    :root {
      --primary: #0F172A;
      --accent: #2563EB;
      --bg: #F8FAFC;
      --card-bg: #FFFFFF;
      --border: #E2E8F0;
      
      /* Severity Colors */
      --critical: #EF4444;
      --high: #F97316;
      --medium: #F59E0B;
      --low: #10B981;
    }
    
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--primary);
      margin: 0;
      padding: 40px;
      line-height: 1.5;
    }
    
    .container {
      max-width: 1000px;
      margin: 0 auto;
    }
    
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid var(--border);
      padding-bottom: 20px;
      margin-bottom: 30px;
    }
    
    .header h1 {
      margin: 0 0 8px 0;
      font-size: 2rem;
      font-weight: 800;
    }

    .header p {
      margin: 0;
      color: #64748B;
    }

    .dashboard-grid {
      display: grid;
      grid-template-columns: 1fr 2fr;
      gap: 30px;
      margin-bottom: 40px;
    }
    
    .card {
      background-color: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    .card h3 {
      margin: 0 0 16px 0;
      font-size: 1.25rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 8px;
    }

    .gauge-container {
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
    
    .score-circle {
      width: 140px;
      height: 140px;
      border-radius: 50%;
      border: 10px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 3rem;
      font-weight: 800;
      margin-bottom: 15px;
    }
    
    .state-badge {
      display: inline-block;
      padding: 6px 12px;
      border-radius: 9999px;
      font-weight: 700;
      text-transform: uppercase;
      font-size: 0.85rem;
    }
    
    .state-ready { background-color: #D1FAE5; color: #065F46; }
    .state-warning { background-color: #FEF3C7; color: #92400E; }
    .state-critical_unprepared { background-color: #FEE2E2; color: #991B1B; }

    .status-item {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
      padding-bottom: 8px;
      border-bottom: 1px dashed var(--border);
    }

    .status-item:last-child {
      border-bottom: none;
      margin-bottom: 0;
      padding-bottom: 0;
    }

    .checklist-table, .inventory-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 15px;
    }
    
    .checklist-table th, .checklist-table td, 
    .inventory-table th, .inventory-table td {
      border: 1px solid var(--border);
      padding: 12px;
      text-align: left;
    }
    
    .checklist-table th, .inventory-table th {
      background-color: #F1F5F9;
      font-weight: 600;
    }
    
    .priority-must { color: var(--critical); font-weight: 700; }
    .priority-should { color: var(--high); font-weight: 700; }
    .priority-could { color: var(--medium); font-weight: 700; }

    .status-completed { color: var(--low); font-weight: 600; }
    .status-pending { color: var(--high); font-weight: 600; }

    .finding-card {
      border-left: 6px solid var(--border);
      margin-bottom: 20px;
      padding: 18px;
    }
    
    .finding-card h4 {
      margin: 0 0 8px 0;
    }

    .severity-critical { border-left-color: var(--critical); }
    .severity-high { border-left-color: var(--high); }
    .severity-medium { border-left-color: var(--medium); }
    .severity-low { border-left-color: var(--low); }

    /* PDF Print Styles override */
    @media print {
      body {
        padding: 0;
        background-color: #FFF;
      }
      .container {
        max-width: 100%;
      }
      .card {
        box-shadow: none;
        page-break-inside: avoid;
      }
      .page-break {
        page-break-before: always;
      }
      thead {
        display: table-header-group;
      }
      tr {
        page-break-inside: avoid;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1>Phoenix Recovery Readiness Report</h1>
        <p>Generated on: {{ generated_at }}</p>
      </div>
      <div>
        <span class="state-badge state-{{ readiness_state | lower }}">{{ readiness_state }}</span>
      </div>
    </div>

    <!-- Section 1: Dashboard -->
    <div class="dashboard-grid">
      <div class="card gauge-container">
        <h3>Readiness Score</h3>
        <div class="score-circle" style="border-color: {% if readiness_state == 'READY' %}var(--low){% elif readiness_state == 'WARNING' %}var(--medium){% else %}var(--critical){% endif %}">
          {{ readiness_score }}
        </div>
        <p><strong>Device:</strong> {{ device_summary.device_name }}</p>
        <p><strong>Model:</strong> {{ device_summary.model }}</p>
        <p><strong>Android:</strong> Version {{ device_summary.android_version }} (API {{ device_summary.api_level }})</p>
      </div>
      
      <div class="card">
        <h3>Device Backup Progress</h3>
        <div class="status-item">
          <span>Contacts Backup:</span>
          <strong>{% if verdicts.contacts_ready %}✅ Secure{% else %}❌ Missing{% endif %}</strong>
        </div>
        <div class="status-item">
          <span>SMS Log Backup:</span>
          <strong>{% if verdicts.sms_ready %}✅ Secure{% else %}❌ Missing{% endif %}</strong>
        </div>
        <div class="status-item">
          <span>Call History Backup:</span>
          <strong>{% if verdicts.call_logs_ready %}✅ Secure{% else %}❌ Missing{% endif %}</strong>
        </div>
        <div class="status-item">
          <span>Storage Synced:</span>
          <strong>{{ device_summary.used_storage_bytes | filesizeformat }} of {{ device_summary.total_storage_bytes | filesizeformat }}</strong>
        </div>
      </div>
    </div>

    <!-- Section 2: Actionable Checklist -->
    <div class="card" style="margin-bottom: 40px;">
      <h3>Actionable Recovery Checklist</h3>
      <table class="checklist-table">
        <thead>
          <tr>
            <th>Priority</th>
            <th>Timing</th>
            <th>Instruction</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {% for item in remediation_checklist %}
          <tr>
            <td><span class="priority-{{ item.priority | lower }}">{{ item.priority }}</span></td>
            <td><code>{{ item.timing }}</code></td>
            <td>{{ item.instruction }}</td>
            <td><span class="status-{{ item.status | lower }}">{{ item.status }}</span></td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <!-- Section 3: Risk Findings -->
    {% if risk_findings %}
    <div class="card page-break" style="margin-bottom: 40px;">
      <h3>Outstanding Application Recovery Risks</h3>
      {% for finding in risk_findings %}
      <div class="card finding-card severity-{{ finding.severity | lower }}">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <h4 style="margin: 0;">{{ finding.app_name }} ({{ finding.package_name }})</h4>
          <span style="font-weight: bold; color: var(--{{ finding.severity | lower }}); font-size: 0.85rem;">{{ finding.severity }}</span>
        </div>
        <p style="margin: 0 0 8px 0;"><strong>Technical Constraint:</strong> {{ finding.reasoning }}</p>
        <p style="margin: 0;"><strong>Required User Action:</strong> {{ finding.remediation }}</p>
      </div>
      {% endfor %}
    </div>
    {% endif %}

    <!-- Section 4: Inventory -->
    <div class="card page-break" style="margin-bottom: 40px;">
      <h3>Complete Application Inventory</h3>
      <table class="inventory-table">
        <thead>
          <tr>
            <th>App Name</th>
            <th>Package Name</th>
            <th>Version</th>
            <th>Allow Backup</th>
            <th>Risk Score</th>
          </tr>
        </thead>
        <tbody>
          {% for app in application_inventory %}
          <tr>
            <td>{{ app.app_name }}</td>
            <td><code>{{ app.package_name }}</code></td>
            <td>{{ app.version_name }}</td>
            <td>{% if app.allow_backup %}Yes{% else %}No{% endif %}</td>
            <td>{{ app.risk_score }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <!-- Section 5: Future/Additional Sections -->
    {% for section in additional_sections %}
    <div class="card page-break" style="margin-bottom: 40px;">
      <h3>{{ section.title }}</h3>
      <div>{{ section.content_html }}</div>
    </div>
    {% endfor %}

  </div>
</body>
</html>
"""


class HtmlReportEngine:
    """
    Engine responsible for taking database assessments and compiling them
    into a beautiful, standalone HTML report with no external dependencies.
    """

    def __init__(self, template_str: Optional[str] = None):
        self.template_str = template_str or DEFAULT_TEMPLATE

    def generate_report(
        self,
        assessment: ReadinessAssessment,
        device_summary: Dict[str, Any],
        output_path: str,
        additional_sections: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Renders the readiness report to an HTML file.
        Returns the rendered HTML string.
        """
        logger.info("Generating HTML Readiness Report to: %s", output_path)
        
        # Compile checklist items
        checklist_items = []
        for t in assessment.checklist:
            checklist_items.append({
                "task_id": t.task_id,
                "priority": t.priority,
                "timing": t.timing,
                "instruction": t.step,
                "status": t.status
            })

        # Compile findings
        findings = []
        for f in assessment.findings:
            findings.append({
                "package_name": f.package_name,
                "app_name": f.app_name,
                "category": f.category,
                "severity": f.severity,
                "reasoning": f.reasoning,
                "remediation": f.remediation,
                "resolved": f.resolved
            })

        # Compile inventory
        inventory = []
        for app in assessment.inventory:
            inventory.append({
                "app_name": app.get("app_name") or app.get("package_name"),
                "package_name": app.get("package_name"),
                "version_name": app.get("version_name") or "1.0",
                "allow_backup": bool(app.get("allow_backup")),
                "risk_score": app.get("risk_score") or 0
            })

        # Construct full template context
        context = {
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "readiness_score": assessment.readiness_score,
            "readiness_state": assessment.readiness_state,
            "verdicts": assessment.verdicts,
            "device_summary": device_summary,
            "remediation_checklist": checklist_items,
            "risk_findings": findings,
            "application_inventory": inventory,
            "additional_sections": additional_sections or []
        }

        # Render HTML using custom TemplateRenderer
        rendered_html = TemplateRenderer.render(self.template_str, context)

        # Write to file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)

        logger.info("Successfully generated standalone HTML report.")
        return rendered_html
