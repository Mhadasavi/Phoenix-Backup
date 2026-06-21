# Phoenix Backup Decision Suite: Recovery Readiness Scoring System Design
## Role: Principal AI Architect
## Execution Context: 100% Offline (Local Client PC)
## Document Version: 1.0.0

---

## 1. Mathematical Scoring Formulation

The Recovery Readiness Score ($S$) is a single metric between $0$ and $100$ that represents the feasibility and safety of restoring a device's data to a new target device without loss of critical access or user files.

The score is computed in two phases:
1.  **Additive Phase:** Calculates the baseline progress based on positive backup achievements across weighted categories.
2.  **Subtractive Phase:** Subtracts penalty modifiers based on unresolved, active risks.

### 1.1 The Score Equation

$$S = \min\left(100, \max\left(0, S_{\text{weighted}} - \sum_{i \in U} P(i)\right)\right)$$

Where:
*   **$S$**: The final Recovery Readiness Score ($S \in [0, 100]$).
*   **$S_{\text{weighted}}$**: The weighted base category score ($S_{\text{weighted}} \in [0, 100]$).
*   **$U$**: The set of all detected high-risk items (vulnerabilities, credentials, local files) currently in an **unresolved** state.
*   **$P(i)$**: The global deduction penalty associated with active risk item $i$.

---

## 2. Category Weighting Strategy

The baseline score ($S_{\text{weighted}}$) is compiled from three independent categories, reflecting distinct data domains:

$$S_{\text{weighted}} = (W_{\text{core}} \cdot C_{\text{core}}) + (W_{\text{storage}} \cdot C_{\text{storage}}) + (W_{\text{apps}} \cdot C_{\text{apps}})$$

Where:
*   $W_{\text{core}} = 0.40$ (Core Communications Data)
*   $W_{\text{storage}} = 0.30$ (User Storage & Media Sync)
*   $W_{\text{apps}} = 0.30$ (Application Readiness baseline)

The sum of all weights equals $1.0$ ($0.40 + 0.30 + 0.30$).

### 2.1 Category Breakdowns & Calculations

#### 2.1.1 Core Communications ($C_{\text{core}}$) - Weight: 40%
This category monitors critical communication assets. These are structured databases that must be exported and verified.
*   **Formula:**
    $$C_{\text{core}} = (w_{\text{contacts}} \cdot I_{\text{contacts}}) + (w_{\text{sms}} \cdot I_{\text{sms}}) + (w_{\text{call}} \cdot I_{\text{call}})$$
*   **Weights within Category:**
    *   $w_{\text{contacts}} = 40$
    *   $w_{\text{sms}} = 40$
    *   $w_{\text{call}} = 20$
*   **Indicators ($I_{\text{contacts}}, I_{\text{sms}}, I_{\text{call}}$):**
    *   Binary indicator ($1$ if backup archive is verified, non-corrupt, and non-empty on the host PC; $0$ otherwise).

#### 2.1.2 User Storage & Media ($C_{\text{storage}}$) - Weight: 30%
Tracks files stored in bulk user storage directories (e.g., Photos, Downloads, Documents).
*   **Formula:**
    $$C_{\text{storage}} = 100 \times \frac{\sum_{d \in D} \text{BytesSynced}(d)}{\sum_{d \in D} \text{TotalBytes}(d)}$$
*   Where $D$ is the set of user-selected directories. If $D$ is empty (user deselected all folders) or total bytes to sync is $0$, $C_{\text{storage}}$ defaults to $100$.

#### 2.1.3 Application Readiness baseline ($C_{\text{apps}}$) - Weight: 30%
Establishes the percentage of applications that have been audited and identified as ready for migration (e.g., standard store apps with cloud backends or low-risk profiles).
*   **Formula:**
    $$C_{\text{apps}} = 100 \times \frac{N_{\text{total}} - N_{\text{high\_risk\_detected}}}{N_{\text{total}}}$$
*   Where $N_{\text{total}}$ is the total count of user-installed apps, and $N_{\text{high\_risk\_detected}}$ is the count of apps flagged as belonging to critical or high risk profiles (authenticators, local messengers, banking apps) before any user resolutions.

---

## 3. Risk Levels & Penalty Rules

If a high-risk application or local file directory is flagged, it is added to the active vulnerability set $U$. The penalties directly subtract from $S_{\text{weighted}}$. This ensures that even if a device has a 100% backup completion, the presence of an un-exported authenticator will force the score down to reflect a dangerous migration state.

### 3.1 Penalty Scaling
Each unresolved item $i \in U$ carries a deduction based on its risk level:

| Risk Level | Penalty $P(i)$ | Definition & Examples |
| :--- | :--- | :--- |
| **Critical** | $20\text{ pts}$ | **Absolute Lockout/Irrecoverable Data:** The data is locked to hardware signatures or sandbox directories with `allowBackup=false`. Examples: *Google Authenticator, Signal history, corporate MDM profile, cryptocurrency seed keys.* |
| **High** | $10\text{ pts}$ | **High Re-authentication Friction:** Restoring will trigger identity checks, hardware locks, or secure vault configuration. Examples: *Chase Mobile, Bitwarden offline vaults, WhatsApp database extraction.* |
| **Medium** | $5\text{ pts}$ | **Minor Local Data Loss:** Custom files or game-save directories that are stored outside standard media paths and lack cloud synchronization. Examples: *Minecraft saves, offline maps, custom drawing app directories.* |
| **Low** | $1\text{ pt}$ | **Configuration Friction:** Basic app settings or cache that require re-configuration but cause no data loss. Examples: *Spotify download cache, custom launcher setups.* |

### 3.2 Mitigation Overrides (Score Recovery)
A penalty is only subtracted if the item is in the **unresolved** set ($U$). When the user performs the manual remediation steps outlined by the engine and checks the item as "Resolved" in the Phoenix desktop UI, the item is moved to the resolved set ($R$).

$$U \leftarrow U \setminus \{i\}$$

This dynamically removes the penalty $P(i)$ from the score equation, immediately raising $S$.

---

## 4. Explainable Scoring Engine

The scoring engine must not present a raw number without explaining *how* the score was derived. The scoring output schema contains a structured `audit_trail` and `assessment` block.

```
+-------------------------------------------------------------+
|               RECOVERY READINESS AUDIT TRAIL                |
+-------------------------------------------------------------+
| Base Category Scores:                                       |
| - Core Communications: 80/100                               |
|   * Contacts: Verified (40 pts)                             |
|   * SMS History: Verified (40 pts)                          |
|   * Call Logs: Missing (0 pts)                              |
| - Storage Sync: 100/100 (12.4 GB synced)                    |
| - App Baseline: 95/100 (2 apps flagged as high-risk)        |
|                                                             |
| Weighted Score: (80 * 0.4) + (100 * 0.3) + (95 * 0.3) = 90.5 |
|                                                             |
| Active Penalties:                                           |
| [CRITICAL] Google Authenticator is Unresolved     (-20 pts) |
| [HIGH]     Signal history backup is Unresolved    (-10 pts) |
|                                                             |
| Final Score calculation: 90.5 - 20 - 10 = 60.5 -> Round: 61 |
| Status: CRITICAL_UNPREPARED (Dangerous to Wipe)             |
+-------------------------------------------------------------+
```

### 4.1 Plain-Language Status Categories
The calculated score maps to three actionable recovery states:

*   **`READY` ($90 \le S \le 100$):**
    *   *User Explanation:* "Your device is fully prepared for recovery. Core communication logs and user storage are backed up. No unresolved critical app warnings remain."
*   **`WARNING` ($70 \le S < 90$):**
    *   *User Explanation:* "Your baseline data is secure, but you have unresolved high-friction apps (like banking profiles) or incomplete media backups. Restoring will require some manual configuration."
*   **`CRITICAL_UNPREPARED` ($0 \le S < 70$):**
    *   *User Explanation:* "DO NOT WIPE OR RESET YOUR PHONE. Core communication databases are missing, or critical authenticator tokens are unresolved. Proceeding now will result in permanent account lockouts or data loss."

---

## 5. Sample Calculations

### Scenario A: Clean Backup with One Critical Blocker
A user has backed up all core items and completed 100% of their storage sync. They have 100 apps installed, only 1 of which is a high-risk application (Google Authenticator) which is unresolved.

1.  **Baseline Category Scores:**
    *   $C_{\text{core}} = (40 \cdot 1) + (40 \cdot 1) + (20 \cdot 1) = 100$
    *   $C_{\text{storage}} = 100$
    *   $C_{\text{apps}} = 100 \times \frac{100 - 1}{100} = 99$
2.  **Weighted Base Score:**
    *   $S_{\text{weighted}} = (0.40 \cdot 100) + (0.30 \cdot 100) + (0.30 \cdot 99) = 40 + 30 + 29.7 = 99.7$
3.  **Active Penalties:**
    *   Google Authenticator is unresolved: $P(i) = 20$
4.  **Final Score:**
    *   $S = 99.7 - 20 = 79.7 \approx 80$ (Status: `WARNING`)
    *   *Explainability:* "Score: 80. You have backed up all files, but Google Authenticator must be manually exported to prevent 2FA lockout."

---

### Scenario B: Incomplete Storage & Multiple Active Risks
A user has backed up contacts and SMS but missed call logs. They synced only 50% of their photos. They have 2 high-risk apps (Signal - Critical, Chase Bank - High) unresolved.

1.  **Baseline Category Scores:**
    *   $C_{\text{core}} = (40 \cdot 1) + (40 \cdot 1) + (20 \cdot 0) = 80$
    *   $C_{\text{storage}} = 50$
    *   $C_{\text{apps}} = 100 \times \frac{100 - 2}{100} = 98$
2.  **Weighted Base Score:**
    *   $S_{\text{weighted}} = (0.40 \cdot 80) + (0.30 \cdot 50) + (0.30 \cdot 98) = 32 + 15 + 29.4 = 76.4$
3.  **Active Penalties:**
    *   Signal unresolved: $P(i) = 20$
    *   Chase Bank unresolved: $P(i) = 10$
    *   Total Penalty = $30$
4.  **Final Score:**
    *   $S = 76.4 - 30 = 46.4 \approx 46$ (Status: `CRITICAL_UNPREPARED`)
    *   *Explainability:* "Score: 46. Missing call history, incomplete media synchronization, and 2 unresolved security/chat databases make this device unsafe to wipe."

---

### Scenario C: Resolved Authenticator Scenario
Same user as Scenario B, but they execute manual backup processes for Signal and verification checklists for Chase Bank, marking both as "Resolved".

1.  **Baseline Category Scores:**
    *   $C_{\text{core}} = 80$
    *   $C_{\text{storage}} = 50$
    *   $C_{\text{apps}} = 98$
2.  **Weighted Base Score:**
    *   $S_{\text{weighted}} = 76.4$
3.  **Active Penalties:**
    *   No unresolved risks ($U = \emptyset$, penalties = $0$)
4.  **Final Score:**
    *   $S = 76.4 - 0 = 76.4 \approx 76$ (Status: `WARNING`)
    *   *Explainability:* "Score: 76. All high-security apps are manually secured. To reach 'Ready' status, complete your media folder sync and back up call history."

---

## 6. Edge Cases & Mitigation Strategies

| Edge Case | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Zero Storage Directories Selected** | Divide-by-zero risk in $C_{\text{storage}}$ calculation. | Default $C_{\text{storage}} = 100$. If the user explicitly selects no directories to back up, storage is considered fully satisfied. |
| **Zero Installed Applications** | Divide-by-zero risk in $C_{\text{apps}}$ calculation. | Default $C_{\text{apps}} = 100$. |
| **Tablet / Data-less Device** | SMS count, Call logs count are naturally 0. $C_{\text{core}}$ is forced down to maximum $40/100$ even with contacts backed up, preventing a tablet from ever reaching `READY` status. | **Dynamic Weight Redistribution:** If device metadata checks reveal no SIM card slot and `api_level` configuration indicates tablet profile, the engine redistributes $C_{\text{core}}$ weights: $w_{\text{contacts}} = 100$, $w_{\text{sms}} = 0$, $w_{\text{call}} = 0$. |
| **Overflow of Penalties** | Penalties exceed $S_{\text{weighted}}$, causing a negative score. | Strict clamping function: $S = \max(0, \text{score})$ ensures the score never drops below $0$. |
| **No Internet Connection** | Scoring cannot query databases for app info. | 100% local operation: Rules engine checks local static `app_rules.json` and local cache. |

---

## 7. Acceptance Criteria

To sign off on the implementation of the Scoring Engine, the developer must verify that the engine complies with the following criteria:

*   **AC-01 (Score Bounds):** The final calculated score must always be an integer value in the inclusive range $[0, 100]$.
*   **AC-02 (Category Independence):** Corruption or failure of user storage sync must not alter the calculations of the core communication database checks.
*   **AC-03 (Explainable Traceability):** The output model must populate the `audit_trail` field listing the exact weights used, the baseline scores, and the individual package names responsible for active deductions.
*   **AC-04 (Override Mechanics):** Toggling an active risk item's state from unresolved to resolved must instantly recalculate the score upwards by the exact value of the penalty.
*   **AC-05 (Dynamic Scale Adjustments):** If an Android device has no cellular capability, the score engine must automatically re-allocate core data category weights to contacts (100%) and suppress call log/SMS expectations.
