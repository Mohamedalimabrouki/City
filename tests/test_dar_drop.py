"""The ground floor of a court house drops its skifa host and turn piece by position, not identity."""
from shapely.geometry import box

from citygen.interior.dar import drop


def test_drop_keeps_an_equal_shared_piece():
    # the cut memos hand out one object for equal inputs: a list may hold the same piece twice
    p, q = box(0, 0, 1, 1), box(1, 0, 2, 1)
    got = drop([p, q, p], 0)
    assert len(got) == 2 and got[0] is q and got[1] is p
    assert [x for x in [p, q, p] if x is not p] == [q]       # the old identity filter lost both
    assert drop([p, q, p], 2) == [p, q] and drop([q], 0) == []
