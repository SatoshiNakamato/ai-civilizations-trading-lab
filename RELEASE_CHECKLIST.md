# Release Checklist

Run this before making a release public.

- [ ] `python -m pytest -q` passes locally and in CI.
- [ ] Worker starts without degraded imports.
- [ ] Multiple runtime cycles complete with `status=ok`.
- [ ] Current RSS telemetry is sane on the target host.
- [ ] Peak RSS and current RSS are reported separately.
- [ ] Adaptive active-agent budget stays within configured bounds.
- [ ] Memory pressure triggers garbage collection and workload reduction.
- [ ] Bounded histories prevent unbounded growth.
- [ ] State survives a worker restart.
- [ ] Twenty civilization systems advance without unbounded state growth.
- [ ] Public-web access remains bounded and domain-controlled.
- [ ] World artifacts remain inside the world boundary.
- [ ] Dry-run research → decision → deployment-policy path succeeds.
- [ ] Risk governor rejects deliberately unsafe candidates.
- [ ] Duplicate execution is prevented.
- [ ] Audit records contain decisions/outcomes but no credentials.
- [ ] Runtime survives an individual cycle exception.
- [ ] Kill switch is verified.
- [ ] Spending/deployment limits are verified.
- [ ] No real credentials, `.env` files, or private state are committed.
- [ ] Release notes and changelog are updated.
- [ ] Version/tag is created only after the above checks pass.

## Live execution gate

Live Bankr execution is a separate operational decision. Passing the software checklist does not by itself authorize funded token deployment.
