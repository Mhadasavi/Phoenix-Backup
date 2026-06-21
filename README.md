# Phoenix Backup Monorepo Skeleton - Sprint 1

This repository contains the Sprint 1 skeleton for **Phoenix Backup** (AI-Powered Android Backup & Recovery Assistant).

## Workspaces Included:
*   `desktop/`: Electron main and React frontend renderer.
*   `shared/`: Common TypeScript types and interface signatures.

## Pre-requisites:
*   Node.js v20+
*   NPM v10+
*   Python v3.10+ (for running tests/mocks)

## Dev Setup:
```bash
# Bootstrap workspaces
npm run bootstrap

# Launch Electron application in development mode
npm run dev:desktop
```

## Running Mocks:
To simulate a connected Android device using the Python mock engine:
```bash
npm run test:mocks:adb
```
