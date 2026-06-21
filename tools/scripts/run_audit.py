#!/usr/bin/env python3
"""
Phoenix Backup Sprint 2 System Integrated Audit CLI Runner
"""

import argparse
import sys
import os
import json

# Adjust path to resolve shared module if run directly from scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from shared.adb.wrapper import AdbWrapper
from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.intelligence.rules import RiskKnowledgeBaseLoader, ApplicationClassifier
from shared.intelligence.classifier import UnknownAppClassifier
from shared.intelligence.findings import FindingsEngine
from shared.intelligence.recommendation import RecoveryRecommendationEngine
from shared.export.html_exporter import HtmlReportEngine
from shared.export.pdf_exporter import PdfReportGenerator
from shared.orchestrator.integration import Sprint2SystemIntegrator

def main():
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True
    )
    parser = argparse.ArgumentParser(description="Phoenix Backup Sprint 2 Diagnostics CLI Runner")
    parser.add_argument("--serial", required=True, help="Android device serial number")
    parser.add_argument("--db", default="phoenix_local.db", help="SQLite database target path")
    parser.add_argument("--output", required=True, help="Output directory for reports and sync directories")
    parser.add_argument("--overrides", default="", help="Comma-separated app packages to mark as user-resolved/overridden")
    parser.add_argument("--adb", default=None, help="Path to adb executable binary")

    args = parser.parse_args()

    # Resolve database path
    db_path = os.path.abspath(args.db)
    output_dir = os.path.abspath(args.output)
    user_overrides = [pkg.strip() for pkg in args.overrides.split(",") if pkg.strip()]

    # Setup rules json path
    rules_path = os.path.join(os.path.dirname(__file__), "../../shared/intelligence/rules.json")
    if not os.path.exists(rules_path):
        rules_path = os.path.join(os.path.dirname(__file__), "../shared/intelligence/rules.json")

    # 1. Initialize DB Connection and apply migrations
    db_manager = DatabaseConnectionManager(db_path)
    try:
        with db_manager.get_connection() as conn:
            migrator = MigrationRunner(conn)
            migrator.run_migrations()
    except Exception as db_err:
        print(json.dumps({"success": False, "error": f"Database initialization failed: {db_err}"}))
        sys.exit(1)

    # 2. Instantiate and load Risk Knowledge Rules
    try:
        rules_loader = RiskKnowledgeBaseLoader(rules_path)
        rules = rules_loader.load_rules()
        app_classifier = ApplicationClassifier(rules)
    except Exception as rule_err:
        print(json.dumps({"success": False, "error": f"Failed loading risk rules base: {rule_err}"}))
        sys.exit(1)

    # 3. Instantiate Orchestrator Abstractions
    try:
        adb_client = AdbWrapper(adb_path=args.adb)
        classifier = UnknownAppClassifier()
        findings_engine = FindingsEngine(app_classifier)
        recommendation_engine = RecoveryRecommendationEngine(classifier)
        html_exporter = HtmlReportEngine()
        pdf_exporter = PdfReportGenerator(output_dir)
    except Exception as init_err:
        print(json.dumps({"success": False, "error": f"Failed instantiating orchestrator modules: {init_err}"}))
        sys.exit(1)

    # 4. Instantiate System Integrator
    integrator = Sprint2SystemIntegrator(
        db_manager=db_manager,
        adb_client=adb_client,
        classifier=classifier,
        findings_engine=findings_engine,
        recommendation_engine=recommendation_engine,
        html_exporter=html_exporter,
        pdf_exporter=pdf_exporter,
        output_dir=output_dir
    )

    # 5. Execute Pipeline Audit
    result = integrator.execute_system_audit(
        serial=args.serial,
        user_overrides=user_overrides
    )

    if result:
        # Load the newly compiled recovery_analysis.json structure to output it
        report_file = os.path.join(output_dir, "recovery_analysis.json")
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                analysis_data = json.load(f)
            
            # Print complete structured output as JSON so Electron main can parse it
            print(json.dumps({
                "success": True,
                "job_id": result["job_id"],
                "readiness_score": result["readiness_score"],
                "readiness_state": result["readiness_state"],
                "report_file": report_file,
                "analysis": analysis_data
            }))
            sys.exit(0)
        except Exception as read_err:
            print(json.dumps({"success": False, "error": f"Failed reading assessment output JSON: {read_err}"}))
            sys.exit(1)
    else:
        print(json.dumps({"success": False, "error": "Integrated diagnostics pipeline run failed."}))
        sys.exit(1)

if __name__ == "__main__":
    main()
