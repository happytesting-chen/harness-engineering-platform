# ATT&CK Technique References

Key MITRE ATT&CK techniques relevant to this engagement.

## Reconnaissance

| ID | Technique | Tool | Notes |
|----|-----------|------|-------|
| T1046 | Network Service Discovery | nmap | Primary scanning tool |
| T1018 | Remote System Discovery | nmap | Host enumeration |
| T1082 | System Information Discovery | nmap -O | OS fingerprinting |

## Initial Access

| ID | Technique | Tool | Notes |
|----|-----------|------|-------|
| T1190 | Exploit Public-Facing Application | Metasploit | Phase-gated until recon passes |
| T1133 | External Remote Services | manual | SSH/RDP if found |

## Privilege Escalation

| ID | Technique | Tool | Notes |
|----|-----------|------|-------|
| T1068 | Exploitation for Privilege Escalation | Metasploit | Requires initial access |
| T1548 | Abuse Elevation Control Mechanism | manual | sudo/SUID analysis |

## Reference

- MITRE ATT&CK: https://attack.mitre.org/
- Engagement follows PTES (Penetration Testing Execution Standard)
