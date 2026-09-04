# Release Checklist

Run this before making a release public.

- [ ] `python -m pytest -q` passes locally and in CI.
- [ ] Worker starts without degraded imports.
- [ ] Multiple runtime cycles complete with `status=ok`.
- [ ] All configured Bankr credentials authenticate without printing secrets.
- [ ] `BANKR_LIVE_DEPLOY` remains disabled during smoke testing.
- [ ] Dry-run research → decision → deployment-policy path succeeds.
- [ ] Risk governor rejects deliberately unsafe candidates.
- [ ] Duplicate execution is prevented.
- [ ] Audit records contain decisions/outcomes but no credentials.
- [ ] Runtime survives an individual cycle exception.
- [ ] State survives a worker restart.
- [ ] Kill switch is verified.
- [ ] Spending/deployment limits are verified.
- [ ] No real credentials, `.env` files, or private state are committed.
- [ ] Release notes and changelog are updated.
- [ ] Tag/version is created only after the above checks pass.

## Live execution gate

Live Bankr execution is a separate operational decision. Passing the software checklist does not by itself authorize funded token deployment.
