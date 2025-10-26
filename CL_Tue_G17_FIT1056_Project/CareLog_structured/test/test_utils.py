
import re
from app.utils import now_iso, check_range

def test_now_iso_format():
    s = now_iso()
    # Expect ISO-like pattern: 2025-01-02T03:04:05+08:00 (timezone may vary)
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", s)

def test_check_range_ok():
    # Should not raise
    check_range(5, 0, 10)

import pytest

def test_check_range_raises_on_out_of_range():
    with pytest.raises(ValueError):
        check_range(11, 0, 10)
