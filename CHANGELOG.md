# Changelog

All notable changes to the Phoenix Backup project will be documented in this file.

## [Unreleased] - 2026-06-21

### Added
- **SMS & Call Logs Extraction**: Integrated pagination loops in `BackupRunner` orchestrator (`backup_runner.py`) to fetch SMS messages (`GET_SMS` command) and Call Logs (`GET_CALL_LOGS` command) sequentially from the Android Companion App.
- **SQLite Database Integration**: Wired the imported payload streams to `BackupImportService.import_sms()` and `BackupImportService.import_call_logs()`, persisting the records and updating job log metrics.
- **Unit Testing**: Extended sequential client mocks and database record validation assertions in `test_backup_runner.py` to ensure complete coverage of SMS and Call history flows.

### Fixed
- **Android Socket Bind Permission Error**: Resolved `bind failed: EPERM` errors on OEM devices by:
  - Adding the `<uses-permission android:name="android.permission.INTERNET" />` to `AndroidManifest.xml`.
  - Upgrading the Zero-UI service to include a `MainActivity` launcher to trigger OEM security settings popups.
  - Bypassing loopback interface bind blocks by binding to wildcard (`0.0.0.0`) and filtering non-loopback clients at the application level.
  - Migrating default communication port from `50051` to `58988` on the service, tunnel commands, and python CLI.
- **Android Content Resolver Query Crash**: Replaced raw SQL `LIMIT` and `OFFSET` sorting tokens in `CallLogProviderHelper` and `SmsProviderHelper` with API 30+ `Bundle` arguments and an in-memory cursor pagination fallback to prevent `Invalid token LIMIT` crashes on Android 15/16 (API 36) physical devices.
- **Python Importer Validation Failure**: Modified `BackupImportService` in `import_service.py` to allow empty string values `""` for phone numbers and SMS addresses (checks for `is None` instead of falsiness), preventing crashes on anonymous call logs or withheld sender IDs.

