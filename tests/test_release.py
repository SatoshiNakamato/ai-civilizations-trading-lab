from civilizations.release import ReleaseChecklist


def test_release_checklist_requires_real_runtime_dependencies():
    checklist = ReleaseChecklist()
    assert checklist.as_dict()["external_outcomes_required"]
    assert checklist.as_dict()["synthetic_market_data_forbidden"]
    assert not checklist.ready(tests_passed=True, external_provider_configured=False, audit_verified=True, lineage_enabled=True)
    assert checklist.ready(tests_passed=True, external_provider_configured=True, audit_verified=True, lineage_enabled=True)
