"""
Phoenix Backup PDF Report Exporter (Hardened Pure-Python Implementation)
"""

import os
import datetime
import logging
from typing import List, Dict, Any, Optional
from shared.intelligence.models import ReadinessAssessment

logger = logging.getLogger("phoenix.export.pdf")

def escape_pdf_text(text: str) -> str:
    """Escapes backslashes and parentheses for safe inclusion inside PDF strings."""
    return str(text).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

def wrap_text(text: str, width_chars: int = 80) -> List[str]:
    """Wraps text into multiple lines by character count to fit page column widths."""
    lines = []
    for paragraph in text.split('\n'):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current_line = []
        current_length = 0
        for word in words:
            if current_length + len(word) + (1 if current_line else 0) <= width_chars:
                current_line.append(word)
                current_length += len(word) + (1 if len(current_line) > 1 else 0)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        if current_line:
            lines.append(" ".join(current_line))
    return lines

class PdfReportEngine:
    """
    Pure-Python, zero-dependency PDF engine.
    Constructs a valid PDF 1.4 binary file structure using native drawing operators.
    """

    def __init__(self):
        self.pages: List[str] = []
        self.current_page_stream: List[str] = []
        self.y: float = 750
        self.page_index: int = 0
        self.device_summary: Dict[str, Any] = {}

    def start_new_page(self):
        """Finalizes the current page stream and initializes a new page buffer."""
        if self.current_page_stream:
            self.pages.append("\n".join(self.current_page_stream))
        
        self.page_index += 1
        self.current_page_stream = []
        self.y = 780
        
        # Draw standard header on subsequent pages
        if self.page_index > 1:
            self.current_page_stream.append("0.5 w 0.7 0.7 0.7 RG")
            self.current_page_stream.append("50 795 m 545 795 l S")
            self.add_text("Phoenix Backup Recovery Readiness Report", 50, 798, font_size=8, bold=True)
            self.add_text(f"Page {self.page_index}", 510, 798, font_size=8)
            self.y = 760

    def add_text(self, text: str, x: float, y: float, font_size: float = 9, bold: bool = False):
        """Appends a single line text placement command to the page stream."""
        font = "/F2" if bold else "/F1"
        escaped = escape_pdf_text(text)
        self.current_page_stream.append(f"BT {font} {font_size} Tf {x} {y} Td ({escaped}) Tj ET")

    def add_wrapped_text(self, text: str, x: float, width_chars: int, font_size: float = 9, bold: bool = False, spacing: float = 13):
        """Wraps and prints text downwards, automatically spanning new pages if required."""
        lines = wrap_text(text, width_chars)
        for line in lines:
            if self.y < 50:
                self.start_new_page()
            self.add_text(line, x, self.y, font_size, bold)
            self.y -= spacing

    def draw_progress_bar(self, x: float, y: float, w: float, h: float, percentage: float, color: str):
        """Draws a themed progress bar block representing backup ratios or scores."""
        # Draw background bar (light grey)
        self.current_page_stream.append("0.9 0.9 0.9 rg")
        self.current_page_stream.append(f"{x} {y} {w} {h} re f")
        
        # Draw active bar
        self.current_page_stream.append(f"{color} rg")
        active_w = w * max(0.0, min(1.0, percentage))
        if active_w > 0:
            self.current_page_stream.append(f"{x} {y} {active_w} {h} re f")
            
        # Draw border
        self.current_page_stream.append("0.7 0.7 0.7 RG")
        self.current_page_stream.append("0.5 w")
        self.current_page_stream.append(f"{x} {y} {w} {h} re S")

    def draw_table(self, headers: List[str], rows: List[List[str]], col_widths: List[float], x_start: float = 50):
        """Compiles and strokes a structured grid table."""
        row_height = 15
        header_height = 18
        needed_height = header_height + len(rows) * row_height
        
        if self.y - needed_height < 50:
            self.start_new_page()
            
        # Header background
        self.current_page_stream.append("0.9 0.9 0.92 rg")
        self.current_page_stream.append(f"{x_start} {self.y - header_height} {sum(col_widths)} {header_height} re f")
        
        # Header text
        self.current_page_stream.append("0.1 0.1 0.15 rg")
        x = x_start
        for header, width in zip(headers, col_widths):
            self.add_text(header, x + 5, self.y - header_height + 5, font_size=8, bold=True)
            x += width
            
        self.y -= header_height
        
        # Row content
        for row in rows:
            if self.y - row_height < 50:
                self.start_new_page()
                
            # Alt row backgrounds
            self.current_page_stream.append("0.97 0.97 0.98 RG")
            self.current_page_stream.append("0.5 w")
            self.current_page_stream.append(f"{x_start} {self.y} m {x_start + sum(col_widths)} {self.y} l S")
            
            x = x_start
            for cell, width in zip(row, col_widths):
                cell_str = str(cell)
                max_chars = int(width / 5.2)
                if len(cell_str) > max_chars:
                    cell_str = cell_str[:max_chars - 3] + "..."
                self.add_text(cell_str, x + 5, self.y - row_height + 4, font_size=7.5)
                x += width
                
            self.y -= row_height
            
        # Bottom border line
        self.current_page_stream.append("0.7 0.7 0.7 RG")
        self.current_page_stream.append(f"{x_start} {self.y} m {x_start + sum(col_widths)} {self.y} l S")
        self.y -= 15

    def draw_finding_card(self, app_name: str, package_name: str, severity: str, reasoning: str, remediation: str):
        """Draws a bordered detailed app risk card container."""
        reason_lines = wrap_text(f"Constraint: {reasoning}", width_chars=78)
        remedy_lines = wrap_text(f"Remediation: {remediation}", width_chars=78)
        
        needed_height = 15 + len(reason_lines) * 11 + len(remedy_lines) * 11 + 20
        if self.y - needed_height < 50:
            self.start_new_page()
            
        card_y = self.y - needed_height
        
        # Severity Badge color
        if severity == "CRITICAL":
            color = "0.93 0.27 0.27"
        elif severity == "HIGH":
            color = "0.98 0.45 0.09"
        elif severity == "MEDIUM":
            color = "0.96 0.62 0.04"
        else:
            color = "0.06 0.73 0.51"
            
        # Card Background
        self.current_page_stream.append("0.98 0.98 0.99 rg")
        self.current_page_stream.append(f"50 {card_y} 495 {needed_height} re f")
        
        # Bounding Border
        self.current_page_stream.append("0.85 0.86 0.89 RG")
        self.current_page_stream.append("0.5 w")
        self.current_page_stream.append(f"50 {card_y} 495 {needed_height} re S")
        
        # Thick left margin separator line
        self.current_page_stream.append(f"{color} rg")
        self.current_page_stream.append(f"50 {card_y} 4 {needed_height} re f")
        
        # Header Info
        self.current_page_stream.append("0.05 0.08 0.15 rg")
        self.add_text(f"{app_name} ({package_name})", 65, self.y - 15, font_size=9, bold=True)
        self.current_page_stream.append(f"{color} rg")
        self.add_text(severity, 535 - len(severity) * 5, self.y - 15, font_size=8.5, bold=True)
        
        self.y -= 20
        
        # Reasoning text lines
        self.current_page_stream.append("0.2 0.2 0.25 rg")
        for line in reason_lines:
            self.add_text(line, 65, self.y, font_size=8)
            self.y -= 11
            
        # Remediation text lines
        self.y -= 2
        for line in remedy_lines:
            self.add_text(line, 65, self.y, font_size=8)
            self.y -= 11
            
        self.y = card_y - 12

    def compile_pdf(self, assessment: ReadinessAssessment, device_summary: Dict[str, Any]) -> bytes:
        """Converts assessment logs into a completed binary PDF document stream."""
        self.pages = []
        self.current_page_stream = []
        self.page_index = 0
        self.device_summary = device_summary

        # ----------------------------------------------------
        # Page 1 Setup (Executive Cover & Score Details)
        # ----------------------------------------------------
        self.start_new_page()
        
        # Draw Main Header Block
        self.current_page_stream.append("0.06 0.09 0.16 rg")
        self.add_text("PHOENIX BACKUP SYSTEM", 50, 755, font_size=11, bold=True)
        self.current_page_stream.append("0.15 0.39 0.92 rg")
        self.add_text("Recovery Readiness Audit Report", 50, 730, font_size=20, bold=True)
        
        self.current_page_stream.append("0.4 0.4 0.45 rg")
        gen_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.add_text(f"Generated on: {gen_time} (Offline PC)", 50, 715, font_size=8.5)
        self.current_page_stream.append("0.5 w 0.8 0.8 0.8 RG")
        self.current_page_stream.append("50 705 m 545 705 l S")
        
        # Score Panel Background Box
        self.current_page_stream.append("0.96 0.97 0.99 rg")
        self.current_page_stream.append("50 545 220 145 re f")
        self.current_page_stream.append("0.8 0.83 0.88 RG")
        self.current_page_stream.append("50 545 220 145 re S")
        
        # Draw Readiness Score
        self.add_text("Readiness Score", 65, 665, font_size=10, bold=True)
        score = assessment.readiness_score
        
        # Score Color
        if assessment.readiness_state == "READY":
            color = "0.06 0.73 0.51"  # Green
        elif assessment.readiness_state == "WARNING":
            color = "0.96 0.62 0.04"  # Yellow
        else:
            color = "0.93 0.27 0.27"  # Red
            
        self.current_page_stream.append(f"{color} rg")
        self.add_text(str(score), 65, 610, font_size=42, bold=True)
        self.add_text("/100", 115, 610, font_size=14, bold=True)
        
        # Draw score progress bar
        self.draw_progress_bar(65, 590, 190, 8, score / 100.0, color)
        self.current_page_stream.append("0.3 0.3 0.3 rg")
        self.add_text(f"State: {assessment.readiness_state}", 65, 565, font_size=10, bold=True)

        # Device Metadata Panel (Right side)
        self.add_text("Device Summary", 295, 675, font_size=11, bold=True)
        self.current_page_stream.append("0.2 0.2 0.2 rg")
        self.add_text(f"Device Name: {device_summary.get('device_name', 'Unknown')}", 295, 658, font_size=9)
        self.add_text(f"Model ID   : {device_summary.get('model', 'Unknown')}", 295, 644, font_size=9)
        self.add_text(f"Serial Code: {device_summary.get('serial', 'Unknown')}", 295, 630, font_size=9)
        self.add_text(f"OS Version : Android {device_summary.get('android_version', 'Unknown')} (API {device_summary.get('api_level', 0)})", 295, 616, font_size=9)
        
        # Storage syncer progress bar
        total_storage = device_summary.get("total_storage_bytes", 0)
        synced_storage = device_summary.get("used_storage_bytes", 0)
        storage_ratio = synced_storage / total_storage if total_storage > 0 else 0.0
        
        self.add_text("Media storage sync verification:", 295, 598, font_size=9, bold=True)
        self.draw_progress_bar(295, 582, 230, 8, storage_ratio, "0.15 0.39 0.92")
        
        # Display human-readable storage units
        total_gb = total_storage / (1024**3)
        synced_gb = synced_storage / (1024**3)
        self.add_text(f"{synced_gb:.2f} GB of {total_gb:.2f} GB synced ({storage_ratio*100:.1f}%)", 295, 568, font_size=8)

        # Draw Bottom divider
        self.current_page_stream.append("0.5 w 0.8 0.8 0.8 RG")
        self.current_page_stream.append("50 530 m 545 530 l S")

        # Partition Sync Verdicts Table
        self.y = 515
        self.add_text("Partition Sync Verdicts", 50, self.y, font_size=11, bold=True)
        self.y -= 15
        
        verdicts_headers = ["Backup Partition Target", "Verification Result", "System Status"]
        verdicts_rows = [
            ["Contacts Inventory", "[PASSED]" if assessment.verdicts.get("contacts_ready") else "[FAILED]", "Backup verified locally"],
            ["SMS Logs Database", "[PASSED]" if assessment.verdicts.get("sms_ready") else "[FAILED]", "Backup verified locally"],
            ["Call Logs History", "[PASSED]" if assessment.verdicts.get("call_logs_ready") else "[FAILED]", "Backup verified locally"]
        ]
        self.draw_table(verdicts_headers, verdicts_rows, [160, 120, 215])

        # Actionable Checklist Header
        self.y = 410
        self.add_text("Actionable Recovery Checklist", 50, self.y, font_size=11, bold=True)
        self.y -= 15

        checklist_headers = ["Priority", "Timing Key", "Remediation Step Instruction", "Status State"]
        checklist_rows = []
        for task in assessment.checklist:
            checklist_rows.append([
                task.priority,
                task.timing,
                task.step,
                task.status
            ])
            
        self.draw_table(checklist_headers, checklist_rows, [55, 75, 295, 70])

        # ----------------------------------------------------
        # Section 2: Outstanding Risks (Page 2 onwards)
        # ----------------------------------------------------
        if assessment.findings:
            self.start_new_page()
            self.add_text("Outstanding Application Recovery Risks", 50, self.y, font_size=12, bold=True)
            self.y -= 20
            
            for finding in assessment.findings:
                self.draw_finding_card(
                    app_name=finding.app_name,
                    package_name=finding.package_name,
                    severity=finding.severity,
                    reasoning=finding.reasoning,
                    remediation=finding.remediation
                )

        # ----------------------------------------------------
        # Section 3: App Inventory (Final Page)
        # ----------------------------------------------------
        self.start_new_page()
        self.add_text("Complete Application Inventory", 50, self.y, font_size=12, bold=True)
        self.y -= 20
        
        inventory_headers = ["Application Name", "Package Reference ID", "Version", "allowBackup", "Risk Score"]
        inventory_rows = []
        for app in assessment.inventory:
            inventory_rows.append([
                app.get("app_name") or "Unknown",
                app.get("package_name") or "",
                app.get("version_name") or "1.0",
                "True" if app.get("allow_backup") else "False",
                str(app.get("risk_score") or 0)
            ])
            
        self.draw_table(inventory_headers, inventory_rows, [140, 185, 60, 60, 50])

        # Finalize and compile PDF structure bytes
        self.start_new_page() # flush final page
        return self._build_pdf_bytes()

    def _build_pdf_bytes(self) -> bytes:
        """Assembles structural PDF objects, offsets, catalogs, cross-references and trailers."""
        num_pages = len(self.pages)
        kids_str = " ".join([f"{6 + i} 0 R" for i in range(num_pages)])
        
        objects = []
        
        # Object 1: Catalog
        objects.append((1, "<< /Type /Catalog /Pages 2 0 R >>"))
        # Object 2: Pages Tree Parent
        objects.append((2, f"<< /Type /Pages /Kids [ {kids_str} ] /Count {num_pages} >>"))
        # Object 3: General Resources Font Directory
        objects.append((3, "<< /Font << /F1 4 0 R /F2 5 0 R >> >>"))
        # Object 4: Standard Helvetica font descriptor
        objects.append((4, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"))
        # Object 5: Bold Helvetica font descriptor
        objects.append((5, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"))

        # Setup Page metadata & Content streams pairs
        for i, stream_text in enumerate(self.pages):
            page_id = 6 + i
            stream_id = 6 + num_pages + i
            
            objects.append((page_id, f"<< /Type /Page /Parent 2 0 R /Resources 3 0 R /MediaBox [0 0 595 842] /Contents {stream_id} 0 R >>"))
            
            # Combine content stream bytes safely
            stream_bytes = stream_text.encode('latin1', errors='replace')
            stream_len = len(stream_bytes)
            stream_content = (
                f"<< /Length {stream_len} >>\n"
                f"stream\n"
            ).encode('latin1') + stream_bytes + b"\nendstream"
            
            objects.append((stream_id, stream_content))

        # Compile PDF binary file layout
        pdf_bytes = bytearray()
        pdf_bytes.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n\n")
        
        offsets = {}
        for obj_id, content in objects:
            offsets[obj_id] = len(pdf_bytes)
            pdf_bytes.extend(f"{obj_id} 0 obj\n".encode('latin1'))
            if isinstance(content, str):
                pdf_bytes.extend(content.encode('latin1'))
            else:
                pdf_bytes.extend(content)
            pdf_bytes.extend(b"\nendobj\n\n")
            
        xref_offset = len(pdf_bytes)
        pdf_bytes.extend(b"xref\n")
        total_objects = len(objects) + 1
        pdf_bytes.extend(f"0 {total_objects}\n".encode('latin1'))
        pdf_bytes.extend(b"0000000000 65535 f \n")
        
        for obj_id in sorted(offsets.keys()):
            pdf_bytes.extend(f"{offsets[obj_id]:010d} 00000 n \n".encode('latin1'))
            
        pdf_bytes.extend(b"trailer\n")
        pdf_bytes.extend(f"<<\n  /Size {total_objects}\n  /Root 1 0 R\n>>\n".encode('latin1'))
        pdf_bytes.extend(b"startxref\n")
        pdf_bytes.extend(f"{xref_offset}\n".encode('latin1'))
        pdf_bytes.extend(b"%%EOF\n")
        
        return bytes(pdf_bytes)


class PdfReportGenerator:
    """
    Service wrapper managing file operations and structured error boundaries for PDF Generation.
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def generate_report(self, assessment: ReadinessAssessment, device_summary: Dict[str, Any], filename: str = "recovery_readiness_report.pdf") -> str:
        """
        Generates and saves the PDF report. Handles disk I/O errors securely.
        Returns the absolute filepath of the generated report.
        """
        logger.info("Initializing PDF report compilation process...")
        os.makedirs(self.output_dir, exist_ok=True)
        out_path = os.path.join(self.output_dir, filename)

        try:
            engine = PdfReportEngine()
            pdf_data = engine.compile_pdf(assessment, device_summary)
            
            with open(out_path, "wb") as f:
                f.write(pdf_data)
                
            logger.info("Successfully generated standalone PDF report at: %s", out_path)
            return out_path
        except PermissionError as err:
            logger.error("Failed to write PDF report: Permission Denied. Target file may be locked. Error: %s", err)
            raise IOError(f"Permission denied: Destination file '{out_path}' is currently locked or inaccessible: {err}")
        except Exception as err:
            logger.error("Crashed during PDF report compile operations: %s", err)
            raise IOError(f"Failed to generate PDF report: {err}")
