import pytest

from saps.domain.invoices import ALLOWED_TRANSITIONS, InvalidTransitionError, InvoiceStatus, ensure_transition

S = InvoiceStatus


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.UPLOADED, S.MATCHING),
        (S.UPLOADED, S.EXCEPTION),
        (S.MATCHING, S.PENDING_APPROVAL),
        (S.EXCEPTION, S.MATCHING),
        (S.EXCEPTION, S.REJECTED),
        (S.PENDING_APPROVAL, S.PENDING_REVIEW),
        (S.PENDING_REVIEW, S.COMPLETED),
    ],
)
def test_lifecycle_allows_the_approved_transitions(current: InvoiceStatus, target: InvoiceStatus) -> None:
    ensure_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.UPLOADED, S.PENDING_REVIEW),
        (S.MATCHING, S.REJECTED),
        (S.PENDING_APPROVAL, S.COMPLETED),
        (S.COMPLETED, S.REJECTED),
        (S.REJECTED, S.MATCHING),
    ],
)
def test_lifecycle_refuses_other_transitions(current: InvoiceStatus, target: InvoiceStatus) -> None:
    with pytest.raises(InvalidTransitionError, match=f"{current} -> {target}"):
        ensure_transition(current, target)


def test_every_status_has_a_transition_entry_and_final_states_have_none() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(InvoiceStatus)
    assert ALLOWED_TRANSITIONS[S.COMPLETED] == ALLOWED_TRANSITIONS[S.REJECTED] == frozenset()
