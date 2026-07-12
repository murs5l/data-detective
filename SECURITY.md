# Security Policy

## Supported Versions

Data Detective is pre-1.0 and released on a rolling basis from `main`. Only
the latest version is supported with security fixes.

| Version      | Supported |
|--------------|-----------|
| latest (main) | ✅       |
| older releases | ❌      |

## Reporting a Vulnerability

If you find a security vulnerability, please **do not open a public GitHub
issue**. Instead, report it privately using
[GitHub's private vulnerability reporting](https://github.com/murs5l/data-detective/security/advisories/new)
(Security tab → Report a vulnerability).

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce it (a minimal CSV or request payload, if applicable)
- Any suggested fix, if you have one

We'll acknowledge your report as soon as possible and follow up with next
steps. Please give us a reasonable amount of time to address the issue
before any public disclosure.

## Scope

Data Detective processes user-supplied CSV files. Relevant vulnerability
classes include (but aren't limited to):

- Arbitrary file read/write via CSV parsing or file upload handling
- Denial of service via malformed or oversized CSV input
- Injection issues in the generated HTML reports (e.g. unescaped user data
  rendered into the static report or web app)
- Issues in the FastAPI backend's upload validation or CORS configuration

Your CSV data is processed in memory / a short-lived temp file and is never
persisted to disk or sent to a third party; reports affecting that guarantee
are especially high priority.
