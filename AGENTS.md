# Repository Instructions

- Run the test suite with `scripts/run-tests.sh`.
- After every change to application code or installed assets, run
  `scripts/install.sh` to replace the installed user-local copy and restart
  `headset-tray.service`, then check the service is active and running.
- Never run `scripts/install-udev-rule.sh` unattended: it uses sudo.
- Commit and push every change to `origin/main` without asking, Markdown
  files included.
