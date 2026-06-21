#!/usr/bin/env python3
"""
Phoenix Backup Sidecar Builder Script (DEB-102 Hardening)
Compiles cli_entry.py into phoenix-core.exe using PyInstaller.
"""

import os
import sys
import shutil

def run_compilation():
    # Define absolute paths
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    entry_point = os.path.join(root_dir, "tools/scripts/cli_entry.py")
    dist_dir = os.path.join(root_dir, "tools/bin/win32")
    build_dir = os.path.join(root_dir, "build/pyinstaller_build")
    spec_dir = os.path.join(root_dir, "build")

    print("[*] Resolving project directories...")
    print(f"[*] Root Directory: {root_dir}")
    print(f"[*] CLI Entry     : {entry_point}")
    print(f"[*] Target Dist   : {dist_dir}")

    # Ensure output dist directory exists
    os.makedirs(dist_dir, exist_ok=True)
    os.makedirs(spec_dir, exist_ok=True)

    # Check for PyInstaller presence
    try:
        import PyInstaller.__main__
    except ImportError:
        print("[!] PyInstaller is not installed in the current environment.", file=sys.stderr)
        print("[!] Please run: pip install pyinstaller", file=sys.stderr)
        sys.exit(1)

    print("[*] Spawning PyInstaller compiler engine...")
    
    # Configure compiler parameters
    # --onefile: Compile to single executable
    # --name: Output binary name
    # --distpath: Target directory
    # --workpath: Temp build directory
    pyinstaller_args = [
        entry_point,
        "--onefile",
        "--name=phoenix-core",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--specpath={spec_dir}",
        "--clean"
    ]

    try:
        # Programmatic call preventing shell string injection vulnerabilities
        PyInstaller.__main__.run(pyinstaller_args)
        print("[*] Sidecar binary compiled successfully.")
        print(f"[*] Executable located at: {os.path.join(dist_dir, 'phoenix-core.exe')}")
    except Exception as err:
        print(f"[!] Compilation failed: {err}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_compilation()
