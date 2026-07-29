# Target Scope — Rules of Engagement

## Authorized Targets

| Network | Description | Status |
|---------|-------------|--------|
| 10.20.0.0/24 | Internal lab network | In scope |
| 10.20.1.0/24 | DMZ services | In scope |
| 192.168.100.0/24 | Red team infrastructure | In scope (own infra) |

## Excluded Targets

| Network | Description | Reason |
|---------|-------------|--------|
| 10.0.0.0/8 (other) | Production networks | Not authorized |
| 172.16.0.0/12 | Corporate infrastructure | Not authorized |
| Any external IP | Internet-facing systems | Out of scope |

## Time Windows

- **Authorized hours:** Monday–Friday, 09:00–18:00 UTC
- **Blackout periods:** None currently defined
- **Engagement duration:** 2 weeks from start date

## Rules of Engagement

1. No denial-of-service attacks
2. No destructive actions on target systems
3. No lateral movement outside authorized subnets
4. All findings documented before exploitation
5. Immediate escalation for critical vulnerabilities
6. No data exfiltration to hosts outside 192.168.100.0/24
