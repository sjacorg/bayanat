---
name: Bug report
about: Create a report to help us improve
title: ''
labels: ''
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Logs**
Add log entries using `journalctl -u bayanat.service` (replace bayanat with the name of service you chose) of errors that appeared in the log when you experienced the issue.

If the issue concerns bulk operations or data import tool, please add log entries from celery service using `journalctl -u bayanat-celery.service`.

**Browser information**
E.g. firefox, chrome, etc..

**Browser console**
Add errors that appeared in the browser console when you experienced the issue. Press F12 in Chrome or Firefox to access the browser console.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Additional context**
Add any other context about the problem here.
