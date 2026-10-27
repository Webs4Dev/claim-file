"""Auth and claim access rules, exercised through the real API.

Uses the local Redis (docker compose) and removes everything it creates.
Claim processing is stubbed out, so no LLM calls are made.
"""

import json
import shutil
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main
from auth.api import SESSION_COOKIE
from auth.store import (
    LOGIN_ATTEMPT_LIMIT,
    REGISTER_IP_LIMIT,
    create_user,
    delete_session,
    find_user_by_email,
    normalize_email,
)
from state.schema import ReviewResult
from state.store import delete_claim, load_claim, redis_client, save_claim

PASSWORD = "correct horse battery"

CLAIM_FORM = {
    "policy_number": "TEST-POL-0000000001",
    "insured_name": "Test Claimant",
    "vehicle_registration_number": "KA 01 AB 1234",
    "accident_date": "01/08/2026",
    "accident_description": "Test accident.",
    "damage_description": "Test damage.",
}


@pytest.fixture
def created():
    """Tracks everything a test creates and deletes it afterwards."""
    record = {"emails": [], "users": [], "claims": [], "clients": [], "ips": {"testclient"}}
    yield record

    for client in record["clients"]:
        delete_session(client.cookies.get(SESSION_COOKIE))
    for ip in record["ips"]:
        redis_client.delete(f"login_fail_ip:{ip}", f"register_ip:{ip}")
    for email in record["emails"]:
        email = normalize_email(email)
        redis_client.delete(f"user_email:{email}")
        for key in redis_client.scan_iter(match=f"login_attempts:{email}:*"):
            redis_client.delete(key)
    for user_id in record["users"]:
        redis_client.delete(f"user:{user_id}")
        for key in redis_client.scan_iter(match=f"claim_submission:{user_id}:*"):
            redis_client.delete(key)
    for claim_id in record["claims"]:
        delete_claim(claim_id)
        shutil.rmtree(main.UPLOAD_DIRECTORY / claim_id, ignore_errors=True)


@pytest.fixture(autouse=True)
def no_processing(monkeypatch):
    monkeypatch.setattr(main, "process_claim", lambda claim_id: None)


def new_client(created, ip=None) -> TestClient:
    if ip:
        created["ips"].add(ip)
    # https so the session cookie is sent back even when COOKIE_SECURE is on.
    base_url = "https://testserver"
    client = (
        TestClient(main.app, base_url=base_url, client=(ip, 50000))
        if ip
        else TestClient(main.app, base_url=base_url)
    )
    created["clients"].append(client)
    return client


def claimant(created, name="Test Claimant") -> TestClient:
    email = f"test-{uuid4().hex[:10]}@claimfile.test"
    created["emails"].append(email)
    client = new_client(created)
    response = client.post(
        "/auth/register",
        json={"email": email, "name": name, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    created["users"].append(response.json()["user_id"])
    return client


def reviewer(created) -> TestClient:
    email = f"reviewer-{uuid4().hex[:10]}@claimfile.test"
    created["emails"].append(email)
    user = create_user(email, "Test Reviewer", PASSWORD, "reviewer")
    created["users"].append(user.user_id)
    client = new_client(created)
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return client


def post_claim(client, files, key=None, form=None):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post(
        "/claims",
        data={"claim_form": json.dumps(form or CLAIM_FORM)},
        files=files,
        headers=headers,
    )


def submit_claim(client, created, key=None, insured_name=None) -> str:
    form = {**CLAIM_FORM, "insured_name": insured_name} if insured_name else None
    response = post_claim(
        client,
        {"policy_schedule": ("policy.pdf", b"%PDF-1.4 test", "application/pdf")},
        key,
        form,
    )
    assert response.status_code == 200, response.text
    claim_id = response.json()["claim_id"]
    created["claims"].append(claim_id)
    return claim_id


# ---------- accounts and sessions ----------


def test_register_creates_claimant_without_signing_in(created):
    email = f"test-{uuid4().hex[:10]}@claimfile.test"
    created["emails"].append(email)
    client = new_client(created)

    response = client.post(
        "/auth/register",
        json={"email": email, "name": "Asha Rao", "password": PASSWORD},
    )

    assert response.status_code == 200
    assert "set-cookie" not in response.headers
    assert client.get("/auth/me").status_code == 401

    me = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    created["users"].append(me.json()["user_id"])
    assert me.json()["role"] == "claimant"
    assert me.json()["name"] == "Asha Rao"


def test_session_cookie_is_http_only(created):
    client = claimant(created)
    email = client.get("/auth/me").json()["email"]

    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})

    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_register_does_not_reveal_existing_emails(created):
    email = f"Test-{uuid4().hex[:10]}@ClaimFile.test"
    new_email = f"test-{uuid4().hex[:10]}@claimfile.test"
    created["emails"] += [email, new_email]
    first = new_client(created).post(
        "/auth/register", json={"email": email, "name": "A", "password": PASSWORD}
    )
    original = find_user_by_email(email)
    created["users"].append(original.user_id)

    taken = new_client(created).post(
        "/auth/register",
        json={"email": email.upper(), "name": "B", "password": "a different password"},
    )
    fresh = new_client(created).post(
        "/auth/register",
        json={"email": new_email, "name": "C", "password": PASSWORD},
    )
    created["users"].append(find_user_by_email(new_email).user_id)

    assert first.status_code == taken.status_code == fresh.status_code == 200
    assert taken.json() == fresh.json()
    assert "set-cookie" not in taken.headers
    # The existing account is untouched.
    assert find_user_by_email(email).model_dump() == original.model_dump()


def test_register_is_rate_limited_per_ip(created):
    client = new_client(created, ip="203.0.113.50")

    def register():
        return client.post(
            "/auth/register",
            json={"email": "not-an-email", "name": "A", "password": PASSWORD},
        )

    for _ in range(REGISTER_IP_LIMIT):
        assert register().status_code == 400

    assert register().status_code == 429


@pytest.mark.parametrize("password", ["short", "x" * 73])
def test_register_rejects_bad_passwords(created, password):
    response = new_client(created).post(
        "/auth/register",
        json={"email": f"test-{uuid4().hex[:10]}@claimfile.test", "name": "A", "password": password},
    )

    assert response.status_code == 400


def test_login_failure_message_does_not_reveal_accounts(created):
    client = claimant(created)
    email = client.get("/auth/me").json()["email"]
    anonymous = new_client(created)

    wrong_password = anonymous.post("/auth/login", json={"email": email, "password": "wrong-password"})
    unknown_email = anonymous.post(
        "/auth/login", json={"email": "nobody-" + email, "password": "wrong-password"}
    )
    created["emails"].append("nobody-" + email)

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_login_locks_after_repeated_failures(created):
    client = claimant(created)
    email = client.get("/auth/me").json()["email"]
    anonymous = new_client(created)

    for _ in range(LOGIN_ATTEMPT_LIMIT):
        anonymous.post("/auth/login", json={"email": email, "password": "wrong-password"})

    locked = anonymous.post("/auth/login", json={"email": email, "password": PASSWORD})

    assert locked.status_code == 429


def test_lockout_from_one_ip_does_not_block_the_owner_elsewhere(created):
    email = claimant(created).get("/auth/me").json()["email"]
    attacker = new_client(created, ip="203.0.113.7")

    for _ in range(LOGIN_ATTEMPT_LIMIT + 1):
        attacker.post("/auth/login", json={"email": email, "password": "wrong-password"})

    owner = new_client(created, ip="198.51.100.20")
    response = owner.post("/auth/login", json={"email": email, "password": PASSWORD})

    assert response.status_code == 200


def test_login_replaces_existing_session(created):
    client = claimant(created)
    email = client.get("/auth/me").json()["email"]
    old_token = client.cookies.get(SESSION_COOKIE)

    client.post("/auth/login", json={"email": email, "password": PASSWORD})

    assert client.cookies.get(SESSION_COOKIE) != old_token
    stale = new_client(created)
    stale.cookies.set(SESSION_COOKIE, old_token)
    assert stale.get("/auth/me").status_code == 401


def test_cross_site_writes_are_blocked(created):
    client = claimant(created)

    blocked = client.post("/auth/logout", headers={"Origin": "http://localhost:6666"})
    allowed = client.post("/auth/logout", headers={"Origin": "http://localhost:5173"})

    assert blocked.status_code == 403
    assert allowed.status_code == 200


def test_logout_ends_session(created):
    client = claimant(created)

    client.post("/auth/logout")

    assert client.get("/auth/me").status_code == 401


def test_claims_require_sign_in(created):
    assert new_client(created).get("/claims").status_code == 401


# ---------- claim access ----------


def claim_ids(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [c["claim_id"] for c in response.json()["claims"]]


def test_claimants_only_see_their_own_claims(created):
    owner = claimant(created)
    other = claimant(created)
    claim_id = submit_claim(owner, created)

    assert owner.get(f"/claims/{claim_id}").status_code == 200
    assert other.get(f"/claims/{claim_id}").status_code == 404
    assert claim_id not in claim_ids(other.get("/claims"))
    assert claim_id in claim_ids(owner.get("/claims"))
    # Filters and search cannot reach another owner's claims either.
    assert claim_id not in claim_ids(other.get("/claims", params={"q": claim_id}))
    assert other.get("/claims").json()["status_counts"] == {}


def test_reviewer_sees_every_claim(created):
    claim_id = submit_claim(claimant(created), created)

    response = reviewer(created).get("/claims", params={"q": claim_id})

    assert claim_ids(response) == [claim_id]


def test_claims_list_is_paginated(created):
    owner = claimant(created)
    first, second, third = (submit_claim(owner, created) for _ in range(3))

    page = owner.get("/claims", params={"limit": 2}).json()
    rest = owner.get("/claims", params={"limit": 2, "offset": 2}).json()

    assert page["total"] == rest["total"] == 3
    assert [c["claim_id"] for c in page["claims"]] == [third, second]
    assert [c["claim_id"] for c in rest["claims"]] == [first]


def test_claims_list_filters_and_counts_by_status(created):
    owner = claimant(created)
    waiting, older_waiting = submit_claim(owner, created), submit_claim(owner, created)
    pending = submit_claim(owner, created)
    for claim_id in (waiting, older_waiting):
        claim = load_claim(claim_id)
        claim.status = "human_approval"
        save_claim(claim)

    response = owner.get(
        "/claims", params={"status": "human_approval,needs_internal_review", "order": "oldest"}
    ).json()

    assert [c["claim_id"] for c in response["claims"]] == [waiting, older_waiting]
    assert response["status_counts"] == {"human_approval": 2, "pending": 1}
    assert pending not in [c["claim_id"] for c in response["claims"]]


def test_claims_list_searches_policyholder_names(created):
    owner = claimant(created)
    marker = uuid4().hex[:8]
    match = submit_claim(owner, created, insured_name=f"Meera {marker}")
    submit_claim(owner, created)

    assert claim_ids(owner.get("/claims", params={"q": marker.upper()})) == [match]


def test_claims_deleted_behind_the_index_drop_out_of_the_list(created):
    owner = claimant(created)
    kept = submit_claim(owner, created)
    gone = submit_claim(owner, created)
    redis_client.delete(f"claim:{gone}")

    first = owner.get("/claims").json()
    second = owner.get("/claims").json()

    assert [c["claim_id"] for c in first["claims"]] == [kept]
    assert first["total"] == second["total"] == 1
    assert redis_client.hget("claims:status", gone) is None


def test_claims_list_rejects_oversized_pages(created):
    assert claimant(created).get("/claims", params={"limit": 1000}).status_code == 422


def test_claim_responses_hide_server_file_paths(created):
    owner = claimant(created)
    claim_id = submit_claim(owner, created)

    body = owner.get(f"/claims/{claim_id}").text

    assert "data/uploads" not in body
    assert "file_path" not in body


def test_invalid_claim_form_names_fields_without_echoing_input(created):
    response = post_claim(
        claimant(created),
        {"policy_schedule": ("policy.pdf", b"%PDF-1.4 test", "application/pdf")},
        form={**CLAIM_FORM, "accident_date": ["<secret-marker>"]},
    )

    assert response.status_code == 400
    assert "accident_date" in response.json()["detail"]
    assert "secret-marker" not in response.text


def test_upload_rejects_unsupported_file_types(created):
    response = post_claim(
        claimant(created),
        {"policy_schedule": ("policy.html", b"<script></script>", "text/html")},
    )

    assert response.status_code == 400


def test_upload_rejects_oversized_files_and_cleans_up(created):
    before = set(main.UPLOAD_DIRECTORY.iterdir())

    response = post_claim(
        claimant(created),
        {
            "policy_schedule": ("policy.pdf", b"%PDF-1.4 ok", "application/pdf"),
            "vehicle_registration": ("rc.pdf", b"0" * (main.MAX_UPLOAD_BYTES + 1), "application/pdf"),
        },
    )

    assert response.status_code == 413
    assert set(main.UPLOAD_DIRECTORY.iterdir()) == before


def test_idempotency_keys_are_scoped_per_user(created):
    key = str(uuid4())

    first = submit_claim(claimant(created), created, key=key)
    second = submit_claim(claimant(created), created, key=key)

    assert first != second


# ---------- decisions ----------


def awaiting_approval(owner, created) -> str:
    claim_id = submit_claim(owner, created)
    claim = load_claim(claim_id)
    claim.status = "human_approval"
    save_claim(claim)
    return claim_id


def test_claimants_see_the_automated_verdict_only_after_a_decision(created):
    owner = claimant(created)
    claim_id = awaiting_approval(owner, created)
    claim = load_claim(claim_id)
    claim.review = ReviewResult(status="APPROVED", summary="Model recommends approval.")
    save_claim(claim)
    reviewer_client = reviewer(created)

    waiting = owner.get(f"/claims/{claim_id}").json()
    for_reviewer = reviewer_client.get(f"/claims/{claim_id}").json()
    listed = owner.get("/claims").json()["claims"][0]

    assert waiting["review"] is None and listed["review"] is None
    assert for_reviewer["review"]["status"] == "APPROVED"

    reviewer_client.post(f"/claims/{claim_id}/reject", json={"reason": "Damage not covered."})
    decided = owner.get(f"/claims/{claim_id}").json()

    assert decided["review"]["status"] == "APPROVED"
    assert decided["human_approval"]["decision"] == "REJECTED"


def test_claimant_cannot_decide_claims(created):
    owner = claimant(created)
    claim_id = awaiting_approval(owner, created)

    response = owner.post(f"/claims/{claim_id}/approve", json={})

    assert response.status_code == 403
    assert load_claim(claim_id).status == "human_approval"


def test_reviewer_decision_records_signed_in_reviewer(created):
    claim_id = awaiting_approval(claimant(created), created)

    response = reviewer(created).post(
        f"/claims/{claim_id}/approve",
        json={"reason": "Evidence checks out.", "decided_by": "Someone Else"},
    )

    assert response.status_code == 200
    decision = response.json()["human_approval"]
    assert decision["decided_by"].startswith("Test Reviewer (")
    assert response.json()["status"] == "complete"


def test_reject_without_a_reason_is_refused(created):
    claim_id = awaiting_approval(claimant(created), created)

    response = reviewer(created).post(f"/claims/{claim_id}/reject", json={"reason": "  "})

    assert response.status_code == 400
    assert load_claim(claim_id).status == "human_approval"


def test_reviewer_cannot_decide_own_claim(created):
    reviewer_client = reviewer(created)
    claim_id = awaiting_approval(reviewer_client, created)

    response = reviewer_client.post(f"/claims/{claim_id}/approve", json={})

    assert response.status_code == 403
    assert load_claim(claim_id).status == "human_approval"


def test_retry_is_reviewer_only(created):
    owner = claimant(created)
    claim_id = submit_claim(owner, created)
    claim = load_claim(claim_id)
    claim.status = "needs_internal_review"
    save_claim(claim)

    assert owner.post(f"/claims/{claim_id}/retry").status_code == 403
    assert reviewer(created).post(f"/claims/{claim_id}/retry").status_code == 200
