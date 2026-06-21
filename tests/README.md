# Phoenix Backup Test Suite - Sprint 1

Contains tests and diagnostic mocks for validating the core discovery and database architectures.

## Contents:
*   `e2e/sprint_1_demo.test.ts`: End-to-end integration checklist matching Sprint 1 demo requirements.
*   `mocks/mock_device.py`: Python mock script simulating physical USB-connected Android devices.

## Running the Mock Device Simulator:
```bash
python mocks/mock_device.py
```
This runs a local localhost process that emulates adb query responses.
