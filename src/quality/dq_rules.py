"""
DQ Rules — Moteur de validation de la qualité des données.
Définit des règles unitaires réutilisables pour valider les DataFrames.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Optional, Any
import re

@dataclass
class DQResult:
    rule_name: str
    column: str
    passed: bool
    score: float
    failed_count: int
    total_count: int
    details: Optional[dict] = None

class DQValidator:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.total_rows = len(df)

    def check_completeness(self, column: str) -> DQResult:
        """Vérifie le taux de valeurs non nulles."""
        if column not in self.df.columns:
            return DQResult("completeness", column, False, 0.0, self.total_rows, self.total_rows)
        
        null_count = self.df[column].isna().sum()
        passed = (null_count == 0)
        score = (self.total_rows - null_count) / self.total_rows if self.total_rows > 0 else 0.0
        
        return DQResult("completeness", column, passed, score, int(null_count), self.total_rows)

    def check_uniqueness(self, column: str) -> DQResult:
        """Vérifie l'absence de doublons."""
        if column not in self.df.columns:
            return DQResult("uniqueness", column, False, 0.0, self.total_rows, self.total_rows)
        
        duplicate_count = self.df[column].duplicated().sum()
        passed = (duplicate_count == 0)
        score = (self.total_rows - duplicate_count) / self.total_rows if self.total_rows > 0 else 0.0
        
        return DQResult("uniqueness", column, passed, score, int(duplicate_count), self.total_rows)

    def check_range(self, column: str, min_val: float, max_val: float) -> DQResult:
        """Vérifie si les valeurs sont dans une plage donnée."""
        if column not in self.df.columns:
            return DQResult("range", column, False, 0.0, self.total_rows, self.total_rows)
        
        out_of_range = self.df[(self.df[column] < min_val) | (self.df[column] > max_val)]
        failed_count = len(out_of_range)
        passed = (failed_count == 0)
        score = (self.total_rows - failed_count) / self.total_rows if self.total_rows > 0 else 0.0
        
        return DQResult("range", column, passed, score, failed_count, self.total_rows)

    def check_regex(self, column: str, pattern: str) -> DQResult:
        """Vérifie la conformité à une expression régulière."""
        if column not in self.df.columns:
            return DQResult("regex", column, False, 0.0, self.total_rows, self.total_rows)
        
        # On ne vérifie que les valeurs non nulles
        mask_not_null = self.df[column].notna()
        def matches(val):
            return bool(re.match(pattern, str(val)))
            
        failed_mask = mask_not_null & (~self.df[column].apply(matches))
        failed_count = failed_mask.sum()
        passed = (failed_count == 0)
        score = (self.total_rows - failed_count) / self.total_rows if self.total_rows > 0 else 0.0
        
        return DQResult("regex", column, passed, score, int(failed_count), self.total_rows)

    def check_freshness(self, column: str, max_age_hours: int) -> DQResult:
        """Vérifie si la donnée est récente (basé sur une colonne timestamp)."""
        if column not in self.df.columns:
            return DQResult("freshness", column, False, 0.0, self.total_rows, self.total_rows)
        
        now = datetime.now(timezone.utc)
        # Conversion si nécessaire
        df_ts = pd.to_datetime(self.df[column])
        if df_ts.dt.tz is None:
            df_ts = df_ts.dt.tz_localize('UTC')
            
        age_hours = (now - df_ts).dt.total_seconds() / 3600
        failed_count = (age_hours > max_age_hours).sum()
        passed = (failed_count == 0)
        score = (self.total_rows - failed_count) / self.total_rows if self.total_rows > 0 else 0.0
        
        return DQResult("freshness", column, passed, score, int(failed_count), self.total_rows)
