import pytest
from pydantic import ValidationError

from app.main import HumanDecisionRequest
from approval.human_gate import approve_claim, reject_claim, request_review
from state.schema import ClaimState, HumanApproval, ReviewResult


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


def auto_rejected_claim():
    return ClaimState(
        claim_id="CLM-TEST",
        status="complete",
        review=ReviewResult(status="REJECTED", summary="Not covered."),
    )


def test_request_review_sends_automatic_rejection_to_a_reviewer():
    claim = request_review(auto_rejected_claim(), "  The survey was misread.  ")

    assert claim.status == "human_approval"
    assert claim.review_request.note == "The survey was misread."
    # The reviewer can now decide it like any other claim.
    assert approve_claim(claim, "Asha Rao").status == "complete"


def test_request_review_note_is_optional():
    assert request_review(auto_rejected_claim(), "   ").review_request.note is None


@pytest.mark.parametrize(
    "claim",
    [
        # Approved automatically: nothing to dispute.
        ClaimState(claim_id="C", status="complete", review=ReviewResult(status="APPROVED", summary="s")),
        # Already decided by a person, so it was asked (or reviewed) once.
        ClaimState(
            claim_id="C",
            status="terminated",
            review=ReviewResult(status="REJECTED", summary="s"),
            human_approval=HumanApproval(
                decision="REJECTED", decided_by="Asha Rao", decided_at="2026-10-27T00:00:00Z"
            ),
        ),
        # Still being processed or already with a reviewer.
        ClaimState(claim_id="C", status="human_approval", review=ReviewResult(status="REJECTED", summary="s")),
        # Stopped at the step limit: no verdict was reached.
        ClaimState(claim_id="C", status="terminated", review=ReviewResult(status="REJECTED", summary="s")),
    ],
)
def test_request_review_only_for_automatic_rejections(claim):
    with pytest.raises(ValueError):
        request_review(claim)
