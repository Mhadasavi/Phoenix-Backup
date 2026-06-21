# Security Policy

We take the security of **Phoenix Backup** seriously. As an application that handles personal data (SMS, Contacts, Call Logs, package lists), security is integrated into our core design guidelines.

## Supported Versions

Only the latest release version is actively supported with security updates.

| Version | Supported |
| :--- | :--- |
| v1.0.x (Sprint 2 MVP) | :white_check_mark: Yes |
| < v1.0 | :x: No |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

If you discover a security vulnerability in this project, please report it to us privately by emailing **security@phoenixbackup.org**. 

Please include:
*   A description of the vulnerability.
*   Steps to reproduce the vulnerability (including proof-of-concept scripts or commands).
*   Any potential impact or exploit scenarios.

We will acknowledge receipt of your report within 48 hours and provide a timeline for resolution.

## Vulnerability Disclosure Timeline

We follow coordinated disclosure principles:
*   We aim to patch critical security issues within 30 days of receipt.
*   Public disclosure will be coordinated with the reporter after a fix has been released.

## Core Security Safeguards
*   **Localhost Isolation:** The Mobile Companion App ServerSocket strictly binds to `127.0.0.1` to prevent remote access over shared network interfaces (e.g. public Wi-Fi).
*   **Token Handshake:** Socket sessions are authenticated using random, single-use intents tokens passed during ADB startup.
*   **No File Caching:** Private data is processed entirely in-memory and never cached on device flash storage.
