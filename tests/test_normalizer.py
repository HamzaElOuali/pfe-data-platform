import pytest
import pandas as pd
import numpy as np
from src.processing.normalizer import (
    fill_missing_numeric, 
    fill_missing_categorical, 
    cap_outliers_iqr, 
    clean_zip_code, 
    clean_string
)

def test_fill_missing_numeric_median():
    df = pd.DataFrame({"val": [10, 20, np.nan, 40, 50]})
    df_filled = fill_missing_numeric(df, "val", strategy="median")
    assert df_filled["val"][2] == 30.0  # Médiane de 10, 20, 40, 50 est 30

def test_fill_missing_categorical():
    df = pd.DataFrame({"cat": ["A", None, "B"]})
    df_filled = fill_missing_categorical(df, "cat", default="missing")
    assert df_filled["cat"][1] == "missing"

def test_cap_outliers_iqr():
    df = pd.DataFrame({"val": [1, 2, 3, 100]}) # 100 est un outlier
    # Q1=1.5, Q3=51.5, IQR=50 -> Upper bound = 51.5 + 1.5*50 = 126.5 (pas d'outlier ici avec peu de points)
    # Essayons avec plus de points
    df = pd.DataFrame({"val": [10, 11, 12, 13, 14, 15, 16, 100]})
    # Q1=11.75, Q3=15.25, IQR=3.5 -> Upper = 15.25 + 1.5*3.5 = 20.5
    df_capped = cap_outliers_iqr(df, "val", factor=1.5)
    assert df_capped["val"].max() < 100
    assert df_capped["val"].iloc[-1] <= 21.0 # Approximatif selon l'implémentation exacte de quantile

def test_clean_zip_code():
    assert clean_zip_code("1234") == "01234"
    assert clean_zip_code("12345-678") == "12345"
    assert clean_zip_code(None) == "00000"

def test_clean_string():
    assert clean_string("  hello world  ") == "HELLO WORLD"
    assert clean_string(None) == ""
