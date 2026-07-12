---
name: Bug report
about: Something isn't working as expected
title: ""
labels: bug
assignees: ""
---

**Describe the bug**
A clear description of what's wrong.

**How are you using Data Detective?**
- [ ] CLI
- [ ] Web app (Docker)
- [ ] Web app (uvicorn, no Docker)
- [ ] REST API directly

**To reproduce**
Steps to reproduce the behavior, ideally with a minimal CSV that triggers it
(a small snippet pasted inline is fine — please don't attach sensitive data):

```csv
col_a,col_b
1,2
3,4
```

Command or request:
```
data-detective analyze sample.csv --html
```

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened. Include the full error message / stack trace if any.

**Environment**
- OS:
- Python version (`python --version`):
- Data Detective version (`pip show data-detective` or commit SHA):
- Installed via: [pip / source / Docker]

**Additional context**
Anything else relevant (file size, number of rows/columns, etc.).
