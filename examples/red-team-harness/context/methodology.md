# Engagement Methodology

ATT&CK-aligned offensive security workflow. Each phase maps to MITRE ATT&CK tactics.

## Phase Flow

```
scope-validation → recon → exploit → report
```

## Phase 1: Scope Validation

**ATT&CK Tactic:** N/A (pre-engagement)

- Confirm target ranges match ROE
- Verify time window is active
- Confirm tooling is operational
- **Exit criteria:** All targets validated against authorized list

## Phase 2: Reconnaissance

**ATT&CK Tactics:** TA0043 (Reconnaissance), TA0007 (Discovery)

- Network scanning (nmap) of in-scope ranges
- Service enumeration and version detection
- OS fingerprinting
- Vulnerability scanning against discovered services
- **Exit criteria:** All in-scope hosts enumerated, services documented

## Phase 3: Exploitation

**ATT&CK Tactics:** TA0001 (Initial Access), TA0004 (Privilege Escalation)

- Exploit identified vulnerabilities
- Attempt privilege escalation on compromised hosts
- Document access level achieved
- **Exit criteria:** Exploitation attempts documented with evidence

## Phase 4: Reporting

**ATT&CK Tactic:** N/A (post-engagement)

- Compile findings with evidence
- Map vulnerabilities to ATT&CK techniques
- Provide remediation recommendations
- **Exit criteria:** Report delivered, all persistence removed
