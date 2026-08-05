# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Bayanat, please report it through [GitHub's private vulnerability reporting](https://github.com/sjacorg/bayanat/security/advisories/new).

Do not open a public issue for security vulnerabilities.

## What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Response

We will acknowledge receipt within 72 hours and provide an initial assessment within 7 business days.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 4.x     | Yes       |
| 3.x     | Yes       |
| < 3.0   | No        |

## Security Practices

- Static analysis via Semgrep and CodeQL
- Dependency scanning via pip-audit and retire.js
- Pre-commit secret scanning via Gitleaks
- GitHub secret scanning with push protection
- Signed commits enforced on protected branches
- Comprehensive [threat model](docs/security/threat-model.md)
