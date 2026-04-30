"""
Normalizer — Fonctions de nettoyage, imputation et gestion des outliers.
Ce module fournit des utilitaires pour préparer les données avant l'ingestion ou pendant la transformation.
"""
import pandas as pd
import numpy as np
import re
from typing import Optional, Union, List

def fill_missing_numeric(df: pd.DataFrame, column: str, strategy: str = "median", fill_value: any = None) -> pd.DataFrame:
    """Impute les valeurs manquantes pour une colonne numérique."""
    if column not in df.columns:
        return df
    
    if strategy == "median":
        val = df[column].median()
    elif strategy == "mean":
        val = df[column].mean()
    elif strategy == "constant":
        val = fill_value
    else:
        raise ValueError(f"Stratégie inconnue : {strategy}")
        
    df[column] = df[column].fillna(val)
    return df

def fill_missing_categorical(df: pd.DataFrame, column: str, default: str = "unknown") -> pd.DataFrame:
    """Impute les valeurs manquantes pour une colonne catégorielle."""
    if column not in df.columns:
        return df
    df[column] = df[column].fillna(default)
    return df

def cap_outliers_iqr(df: pd.DataFrame, column: str, factor: float = 1.5) -> pd.DataFrame:
    """
    Applique le capping (Winsorizing) sur les outliers en utilisant la méthode IQR.
    Les valeurs au-delà de Q3 + factor*IQR ou en dessous de Q1 - factor*IQR sont limitées.
    """
    if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
        return df
        
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - factor * IQR
    upper_bound = Q3 + factor * IQR
    
    df[column] = np.where(df[column] < lower_bound, lower_bound, df[column])
    df[column] = np.where(df[column] > upper_bound, upper_bound, df[column])
    
    return df

def validate_regex(value: str, pattern: str) -> bool:
    """Vérifie si une valeur correspond à un pattern regex."""
    if pd.isna(value) or value is None:
        return False
    return bool(re.match(pattern, str(value)))

def clean_zip_code(value: any) -> str:
    """Normalise un code postal (5 chiffres)."""
    if pd.isna(value) or value is None:
        return "00000"
    # Garder seulement les chiffres
    clean_val = "".join(filter(str.isdigit, str(value)))
    # Prendre les 5 premiers et pad avec des zéros si besoin
    return clean_val[:5].zfill(5)

def clean_string(value: any) -> str:
    """Nettoyage générique de string : strip et upper."""
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip().upper()
