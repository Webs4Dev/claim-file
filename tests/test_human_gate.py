import pytest
from pydantic import ValidationError

from app.main import HumanDecisionRequest
from approval.human_gate import approve_claim, reject_claim
from state.schema import ClaimState


def awaiting_claim(status="human_approval"):
    return ClaimState(claim_id="CLM-TEST", status=status)


def test_approve_moves_claim_to_complete():
    claim = approve_claim(awaiting_claim(), " Asha Rao ", "Evidence checks out.")

    assert claim.status == "complete"
    assert claim.human_approval.decision == "APPROVED"
    assert claim.human_approval.decided_by == "Asha Rao"
    assert claim.human_approval.reason == "Evidence checks out."


def test_reject_moves_claim_to_terminated():
    claim = reject_claim(awaiting_claim(), "Asha Rao", "Damage predates policy.")

    assert claim.status == "terminated"
    assert claim.human_approval.decision == "REJECTED"


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_reject_requires_a_reason(reason):
    with pytest.raises(ValueError):
        reject_claim(awaiting_claim(), "Asha Rao", reason)


@pytest.mark.parametrize("status", ["needs_internal_review", "budget_exceeded"])
def test_stalled_claims_can_be_decided(status):
    claim = reject_claim(awaiting_claim(status), "Asha Rao", "Cannot verify the loss.")

    assert claim.status == "terminated"


@pytest.mark.parametrize("decide", [approve_claim, reject_claim])
def test_decision_requires_human_approval_status(decide):
    with pytest.raises(ValueError):
        decide(awaiting_claim("in_progress"), "Asha Rao")


@pytest.mark.parametrize("decide", [approve_claim, reject_claim])
def test_decision_requires_reviewer_name(decide):
    with pytest.raises(ValueError):
        decide(awaiting_claim(), "   ")


def test_decision_request_limits_reason_length():
    with pytest.raises(ValidationError):
        HumanDecisionRequest(reason="x" * 2001)
