# Build and Run Guide: Phoenix Backup

This guide details the prerequisites, environment setup, test execution, and application launch procedures for **Windows**, **macOS**, and **Linux** developer environments.

---

## 1. Prerequisites

Ensure you have the following runtimes and tools installed on your host machine:

*   **Node.js** v20+ & **NPM** v10+
*   **Python** v3.10+ (and `pip`)
*   **Git**
*   **Android SDK Platform Tools (ADB)**:
    *   The `adb` executable must be available in your system path.
    *   To verify installation, run: `adb version`

> [!WARNING]
> Since the local mock device server emulates an Android device by binding to the default ADB port (**5037**), any running instance of the official Android Debug Bridge server will conflict. You must terminate any active ADB server before starting the mock device server.

---

## 2. Monorepo Setup & Dependency Installation

Phoenix Backup is structured as an NPM monorepo workspace. To bootstrap the project and download all native binaries (Electron shell, precompiled SQLite bindings) without needing full C++ build toolchains (like MSVC / Xcode), execute the platform-specific steps below:

### Windows (CMD / PowerShell)

1.  **Bootstrap NPM Workspaces:**
    ```powershell
    npm.cmd run bootstrap
    ```
    *(This runs `npm install --ignore-scripts` to prevent native compilation failures from blocking the workspace setup.)*

2.  **Download Electron Binary Assets:**
    ```powershell
    node node_modules/electron/install.js
    ```

3.  **Fetch Precompiled SQLite Bindings (`better-sqlite3`):**
    ```powershell
    npx.cmd --yes prebuild-install --platform=win32 --arch=x64 --runtime=electron --target=30.0.1 --cwd node_modules/better-sqlite3
    ```

### macOS (Terminal)

1.  **Bootstrap NPM Workspaces:**
    ```bash
    npm run bootstrap
    ```

2.  **Download Electron Binary Assets:**
    ```bash
    node node_modules/electron/install.js
    ```

3.  **Fetch Precompiled SQLite Bindings (`better-sqlite3`):**
    *   **For Apple Silicon (M1/M2/M3/M4):**
        ```bash
        npx --yes prebuild-install --platform=darwin --arch=arm64 --runtime=electron --target=30.0.1 --cwd node_modules/better-sqlite3
        ```
    *   **For Intel Macs:**
        ```bash
        npx --yes prebuild-install --platform=darwin --arch=x64 --runtime=electron --target=30.0.1 --cwd node_modules/better-sqlite3
        ```

### Linux (Terminal)

1.  **Bootstrap NPM Workspaces:**
    ```bash
    npm run bootstrap
    ```

2.  **Download Electron Binary Assets:**
    ```bash
    node node_modules/electron/install.js
    ```

3.  **Fetch Precompiled SQLite Bindings (`better-sqlite3`):**
    ```bash
    npx --yes prebuild-install --platform=linux --arch=x64 --runtime=electron --target=30.0.1 --cwd node_modules/better-sqlite3
    ```

---

## 3. Mock ADB Server Configuration

If you do not have a physical Android device connected or want to run tests/simulations in a deterministic, sandboxed environment, you can run the local mock ADB server.

> [!IMPORTANT]
> You must kill any active ADB daemon running on your computer first to free up port **5037**:
> *   **All Platforms**: `adb kill-server`

### Launch the Mock ADB Server:
*   **Windows**:
    ```powershell
    py tests/mocks/mock_device.py
    ```
*   **macOS & Linux**:
    ```bash
    python3 tests/mocks/mock_device.py
    ```

Once running, the mock server listens on `127.0.0.1:5037` and responds to basic device connection and application list queries.

---

## 4. Test Suite Execution

The repository features a unified Python unit test and integration/acceptance test suite covering connection logic, inventory crawlers, risk classification rules, and PDF/HTML report generation.

### Run Shared Module Tests (Unit Level)
*   **Windows**:
    ```powershell
    py -m unittest discover -s shared -p "test_*.py"
    ```
*   **macOS & Linux**:
    ```bash
    python3 -m unittest discover -s shared -p "test_*.py"
    ```

### Run System E2E Acceptance Tests
*   **Windows**:
    ```powershell
    py -m unittest discover -s tests -p "test_*.py"
    ```
*   **macOS & Linux**:
    ```bash
    python3 -m unittest discover -s tests -p "test_*.py"
    ```

---

## 5. Launching the Application

### 5.1 Launch Desktop Application (Dev Mode)
To compile the TypeScript/React web views and open the Electron shell:

*   **Windows**:
    ```powershell
    npm.cmd run dev:desktop
    ```
*   **macOS & Linux**:
    ```bash
    npm run dev:desktop
    ```

Upon launch:
1. Webpack compiles the renderer TSX bundles to `./desktop/dist/renderer` and the main process to `./desktop/dist/main`.
2. The Electron main process launches and initializes a local SQLite database at the user app data directory (e.g., `AppData/Roaming/desktop/phoenix_local.db` on Windows) and executes database migrations automatically.

### 5.2 Run Offline Risk Auditor Simulation CLI
To run the host-side console auditor flow using the mock device runner:

1. Ensure the Mock ADB Server is running (see **Section 3** above).
2. Execute the Sprint 2 assessment pipeline:
    *   **Windows**:
        ```powershell
        py tools/scripts/demo_sprint2.py
        ```
    *   **macOS & Linux**:
        ```bash
        python3 tools/scripts/demo_sprint2.py
        ```
3. The script executes the entire 7-phase flow and exports the generated recovery assets (JSON, HTML reports) into the `./demo_reports/` directory.
