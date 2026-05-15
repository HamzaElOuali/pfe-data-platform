"""
Scoring Pipeline en Cascade pour la plateforme E-Commerce Intelligence.

Architecture : M1 (LightGBM Regressor) -> M2 (XGBoost Classifier) -> M3 (KMeans + StandardScaler)
Chaque modele enrichit le suivant : la sortie de M1 alimente M2, la sortie de M2 alimente M3.

Usage :
    pipeline = ScoringPipeline("models")
    result = pipeline.predict({"distance_km": 500, ...})
    batch  = pipeline.predict_batch(dataframe)
"""

import logging
import pathlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger("scoring_pipeline")


class ScoringPipeline:
    """Charge les artefacts ML et execute le scoring en cascade."""

    FEATURES_M1: List[str] = ["distance_km", "total_freight", "order_month", "order_day_of_week"]
    FEATURES_M2: List[str] = ["predicted_delay", "total_items_price", "review_score"]
    FEATURES_M3: List[str] = ["risk_proba", "total_items_price", "nb_items"]

    def __init__(self, models_path: str = "models") -> None:
        self._base = pathlib.Path(models_path)
        self.m1: Any = None
        self.m2: Any = None
        self.m3: Any = None
        self.scaler: Any = None
        self.segment_map: Dict[int, str] = {}
        self._load_models()

    # ------------------------------------------------------------------
    # Chargement des artefacts
    # ------------------------------------------------------------------
    def _load_models(self) -> None:
        """Charge les 5 fichiers pkl depuis le disque."""
        try:
            self.m1 = joblib.load(self._base / "model1_delay.pkl")
            logger.info("M1 (LightGBM Regressor) charge")
        except Exception as exc:
            raise RuntimeError(f"Impossible de charger model1_delay.pkl : {exc}") from exc

        try:
            self.m2 = joblib.load(self._base / "model2_risk.pkl")
            logger.info("M2 (XGBoost Classifier) charge")
        except Exception as exc:
            raise RuntimeError(f"Impossible de charger model2_risk.pkl : {exc}") from exc

        try:
            self.m3 = joblib.load(self._base / "model3_segment.pkl")
            logger.info("M3 (KMeans) charge")
        except Exception as exc:
            raise RuntimeError(f"Impossible de charger model3_segment.pkl : {exc}") from exc

        try:
            self.scaler = joblib.load(self._base / "scaler3.pkl")
            logger.info("StandardScaler charge")
        except Exception as exc:
            raise RuntimeError(f"Impossible de charger scaler3.pkl : {exc}") from exc

        try:
            self.segment_map = joblib.load(self._base / "segment_map.pkl")
            logger.info("Segment map charge : %s", self.segment_map)
        except Exception as exc:
            raise RuntimeError(f"Impossible de charger segment_map.pkl : {exc}") from exc

    # ------------------------------------------------------------------
    # Scoring unitaire
    # ------------------------------------------------------------------
    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Execute la cascade M1 -> M2 -> M3 sur une observation unique."""

        # --- Etape 1 : Prediction du delai (M1) --------------------------
        try:
            m1_input = pd.DataFrame([{k: features[k] for k in self.FEATURES_M1}])
            predicted_delay: float = float(self.m1.predict(m1_input)[0])
        except KeyError as exc:
            raise ValueError(f"Feature manquante pour M1 : {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Erreur M1 (Delay) : {exc}") from exc

        # --- Etape 2 : Evaluation du risque (M2) -------------------------
        try:
            m2_row = {
                "predicted_delay": predicted_delay,
                "total_items_price": features["total_items_price"],
                "review_score": features["review_score"],
            }
            m2_input = pd.DataFrame([m2_row])[["predicted_delay", "total_items_price", "review_score"]]
            risk_proba: float = float(self.m2.predict_proba(m2_input)[0, 1])
            risk_label: int = int(risk_proba >= 0.5)
        except KeyError as exc:
            raise ValueError(f"Feature manquante pour M2 : {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Erreur M2 (Risk) : {exc}") from exc

        # --- Etape 3 : Segmentation (M3) ---------------------------------
        try:
            m3_raw = np.array([[risk_proba, features["total_items_price"], features["nb_items"]]])
            m3_scaled = self.scaler.transform(m3_raw)
            cluster: int = int(self.m3.predict(m3_scaled)[0])
            segment: str = self.segment_map.get(cluster, "Unknown")
        except KeyError as exc:
            raise ValueError(f"Feature manquante pour M3 : {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Erreur M3 (Segment) : {exc}") from exc

        # --- Seuils risk_level --------------------------------------------
        if risk_proba < 0.35:
            risk_level = "Low"
        elif risk_proba < 0.65:
            risk_level = "Medium"
        else:
            risk_level = "High"

        return {
            "predicted_delay_days": round(predicted_delay, 2),
            "risk_proba": round(risk_proba, 4),
            "risk_label": risk_label,
            "risk_level": risk_level,
            "segment": segment,
            "confidence_score": round(max(risk_proba, 1 - risk_proba), 4),
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Scoring batch
    # ------------------------------------------------------------------
    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Score un DataFrame complet de maniere vectorisee (haute performance)."""
        if df.empty:
            return df

        # Selectionner uniquement les colonnes numeriques utiles et gerer les NaN
        all_features = self.FEATURES_M1 + ["review_score", "total_items_price", "nb_items"]
        # Garder order_key si disponible pour la traçabilite
        id_cols = [c for c in ["order_key"] if c in df.columns]
        df = df[id_cols + all_features].copy()
        df[all_features] = df[all_features].apply(pd.to_numeric, errors="coerce").fillna(0)

        # --- Etape 1 : M1 (Delay) ---
        m1_input = df[self.FEATURES_M1]
        df["predicted_delay_days"] = self.m1.predict(m1_input).round(2)
        
        # --- Etape 2 : M2 (Risk) ---
        df["predicted_delay"] = df["predicted_delay_days"] # Create training feature name
        m2_input = df[self.FEATURES_M2]
        risk_probas = self.m2.predict_proba(m2_input)[:, 1]
        df["risk_proba"] = risk_probas.round(4)
        df["risk_label"] = (risk_probas >= 0.5).astype(int)
        
        # --- Risk Level (Numpy vectorize) ---
        df["risk_level"] = np.select(
            [df["risk_proba"] < 0.35, df["risk_proba"] < 0.65],
            ["Low", "Medium"],
            default="High"
        )
        
        # --- Etape 3 : M3 (Segment) ---
        m3_raw = df[self.FEATURES_M3].values
        m3_scaled = self.scaler.transform(m3_raw)
        clusters = self.m3.predict(m3_scaled)
        df["cluster"] = clusters
        df["customer_segment"] = df["cluster"].map(self.segment_map).fillna("Unknown")
        
        df["confidence_score"] = np.maximum(df["risk_proba"], 1 - df["risk_proba"]).round(4)
        df["scored_at"] = datetime.now(timezone.utc).isoformat()
        
        return df


def run_batch_scoring():
    """Fonction principale pour Airflow ou execution manuelle : 
    DuckDB -> Scoring -> PostgreSQL.
    """
    import os
    import duckdb
    from sqlalchemy import create_engine
    from dotenv import load_dotenv
    load_dotenv()

    print("INFO: Initialisation du pipeline...")
    pipeline = ScoringPipeline("models")
    
    # 1. Lire les donnees depuis DuckDB
    db_path = os.getenv("DUCKDB_DATABASE_PATH", "data/processed/warehouse.duckdb")
    print(f"INFO: Lecture des donnees depuis DuckDB ({db_path})...")
    con_duck = duckdb.connect(database=db_path, read_only=True)
    df = con_duck.execute("SELECT * FROM main.mart_ml_prediction_master").df()
    con_duck.close()
    
    if df.empty:
        print("WARNING: Aucune donnee trouvee dans DuckDB.")
        return

    # 2. Scoring
    print(f"INFO: Scoring de {len(df)} lignes (Cascade)...")
    df_scored = pipeline.predict_batch(df)
    
    # 3. Sauvegarde dans PostgreSQL
    host = os.getenv("POSTGRES_DWH_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_DWH_PORT", "5433")
    user = os.getenv("POSTGRES_DWH_USER", "admin")
    password = os.getenv("POSTGRES_DWH_PASSWORD", "admin")
    dbname = os.getenv("POSTGRES_DWH_DB", "dwh_db")
    
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    engine = create_engine(db_url)
    
    # On ne garde que les colonnes essentielles pour Postgres
    cols_to_keep = ['order_key', 'predicted_delay_days', 'risk_proba', 'customer_segment']
    final_df = df_scored[cols_to_keep]
    
    print(f"INFO: Sauvegarde de {len(final_df)} predictions dans PostgreSQL (quality.ml_predictions)...")
    final_df.to_sql('ml_predictions', engine, schema='quality', if_exists='replace', index=False)
    print("SUCCESS: Table quality.ml_predictions mise a jour avec succes.")

if __name__ == "__main__":
    run_batch_scoring()
