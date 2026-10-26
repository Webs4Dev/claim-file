from agents.investigator import (
    apply_intoxication_check,
    reconcile_overall_status,
)
from state.schema import (
    ACCIDENT_INFO,
    POLICY_VALIDITY,
    ClaimExtraction,
    DriverDetails,
    InvestigationFinding,
    InvestigationResult,
)


def finding(category, status):
    return InvestigationFinding(
        category=category,
        status=status,
        finding="finding",
        evidence="evidence",
    )


def intoxicated_extraction():
    return ClaimExtraction(
        driver=DriverDetails(
            condition_at_accident="BAC 0.11%",
            intoxication_reported=True,
        )
    )


def test_intoxication_marks_concern_finding_invalid():
    investigation = InvestigationResult(
        overall_status="CONCERN",
        findings=[finding(ACCIDENT_INFO, "CONCERN")],
    )

    apply_intoxication_check(investigation, intoxicated_extraction())

    assert investigation.findings[0].status == "INVALID"
    assert "BAC 0.11%" in investigation.findings[0].evidence
    assert investigation.overall_status == "INVALID"


def test_intoxication_adds_missing_accident_finding():
    investigation = InvestigationResult(
        overall_status="VALID",
        findings=[finding(POLICY_VALIDITY, "VALID")],
    )

    apply_intoxication_check(investigation, intoxicated_extraction())

    accident = [
        f for f in investigation.findings if f.category == ACCIDENT_INFO
    ]
    assert len(accident) == 1
    assert accident[0].status == "INVALID"


def test_no_intoxication_leaves_investigation_unchanged():
    investigation = InvestigationResult(
        overall_status="VALID",
        findings=[finding(ACCIDENT_INFO, "VALID")],
    )

    apply_intoxication_check(investigation, ClaimExtraction())

    assert investigation.findings[0].status == "VALID"
    assert investigation.overall_status == "VALID"


def test_reconcile_invalid_finding_forces_invalid_overall():
    investigation = InvestigationResult(
        overall_status="CONCERN",
        findings=[
            finding(POLICY_VALIDITY, "VALID"),
            finding(ACCIDENT_INFO, "INVALID"),
        ],
    )

    reconcile_overall_status(investigation)

    assert investigation.overall_status == "INVALID"


def test_reconcile_unsupported_invalid_drops_to_worst_finding():
    investigation = InvestigationResult(
        overall_status="INVALID",
        findings=[
            finding(POLICY_VALIDITY, "VALID"),
            finding(ACCIDENT_INFO, "CONCERN"),
        ],
    )

    reconcile_overall_status(investigation)

    assert investigation.overall_status == "CONCERN"


def test_reconcile_unsupported_invalid_with_all_valid_becomes_concern():
    investigation = InvestigationResult(
        overall_status="INVALID",
        findings=[finding(POLICY_VALIDITY, "VALID")],
    )

    reconcile_overall_status(investigation)

    assert investigation.overall_status == "CONCERN"


def test_reconcile_raises_valid_overall_to_worst_finding():
    investigation = InvestigationResult(
        overall_status="VALID",
        findings=[
            finding(POLICY_VALIDITY, "VALID"),
            finding(ACCIDENT_INFO, "INSUFFICIENT_EVIDENCE"),
        ],
    )

    reconcile_overall_status(investigation)

    assert investigation.overall_status == "INSUFFICIENT_EVIDENCE"


def test_reconcile_keeps_stricter_overall():
    # e.g. CONCERN set because of contradictions, though every finding is VALID
    investigation = InvestigationResult(
        overall_status="CONCERN",
        findings=[finding(POLICY_VALIDITY, "VALID")],
    )

    reconcile_overall_status(investigation)

    assert investigation.overall_status == "CONCERN"
