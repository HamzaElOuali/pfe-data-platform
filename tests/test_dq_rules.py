import pytest
import pandas as pd
import numpy as np
from src.quality.dq_rules import DQValidator

def test_check_completeness():
    df = pd.DataFrame({"id": [1, 2, None]})
    validator = DQValidator(df)
    result = validator.check_completeness("id")
    assert result.passed == False
    assert result.score == pytest.approx(2/3, 0.01)
    assert result.failed_count == 1

def test_check_uniqueness():
    df = pd.DataFrame({"pk": [1, 1, 2]})
    validator = DQValidator(df)
    result = validator.check_uniqueness("pk")
    assert result.passed == False
    assert result.failed_count == 1

def test_check_range():
    df = pd.DataFrame({"score": [1, 5, 6, 0]})
    validator = DQValidator(df)
    result = validator.check_range("score", 1, 5)
    assert result.passed == False
    assert result.failed_count == 2 # 6 et 0 sont hors plage

def test_check_regex():
    df = pd.DataFrame({"zip": ["12345", "1234", "ABCDE"]})
    validator = DQValidator(df)
    result = validator.check_regex("zip", r"^\d{5}$")
    assert result.passed == False
    assert result.failed_count == 2
    assert result.score == pytest.approx(1/3, 0.01)
