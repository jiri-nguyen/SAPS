import pytest

from saps.domain.invoices import ALLOWED_TRANSITIONS, InvalidTransitionError, InvoiceStatus, ensure_transition

S = InvoiceStatus


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.UPLOADED, S.MATCHING),
        (S.UPLOADED, S.EXCEPTION),
        (S.MATCHING, S.PENDING_APPROVAL),
        (S.MATCHING, S.POSTING),  # SAPS-49 BR-01
        (S.EXCEPTION, S.MATCHING),
        (S.EXCEPTION, S.REJECTED),
        (S.PENDING_APPROVAL, S.POSTING),
        (S.PENDING_APPROVAL, S.REJECTED),
        (S.PENDING_REVIEW, S.POSTING),  # the upgrade only (BR-10)
        (S.POSTING, S.POSTED),
    ],
)
def test_lifecycle_allows_the_approved_transitions(current: InvoiceStatus, target: InvoiceStatus) -> None:
    ensure_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.UPLOADED, S.PENDING_REVIEW),
        (S.UPLOADED, S.POSTING),
        (S.MATCHING, S.REJECTED),
        (S.MATCHING, S.PENDING_REVIEW),  # no final review any more (DEC-063)
        (S.EXCEPTION, S.POSTING),  # acceptance goes through Matching
        (S.EXCEPTION, S.PENDING_APPROVAL),
        (S.PENDING_APPROVAL, S.COMPLETED),
        (S.PENDING_REVIEW, S.COMPLETED),
        (S.PENDING_REVIEW, S.REJECTED),
        (S.POSTING, S.REJECTED),  # BR-07, EC-10
        (S.POSTING, S.MATCHING),
        (S.POSTED, S.REJECTED),
        (S.COMPLETED, S.REJECTED),
        (S.REJECTED, S.MATCHING),
    ],
)
def test_lifecycle_refuses_other_transitions(current: InvoiceStatus, target: InvoiceStatus) -> None:
    with pytest.raises(InvalidTransitionError, match=f"{current} -> {target}"):
        ensure_transition(current, target)


def test_every_status_has_a_transition_entry_and_final_states_have_none() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(InvoiceStatus)
    for final in (S.COMPLETED, S.REJECTED, S.POSTED):
        assert ALLOWED_TRANSITIONS[final] == frozenset()
