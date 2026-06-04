"""
Scoring Pipeline en Cascade — E-Commerce Intelligence Platform.

Architecture : M1 (LightGBM) -> M2 (XGBoost) -> Regle deterministe (Segmentation)
M1 predit le delai de livraison.
M2 predit le risque NPS (retard OU mauvaise note).
La regle deterministe classe le client en VIP/Loyal/At Risk/Lost
selon risk_proba x total_items_price.

Correction v2 : _segment_rule() remplace model3.predict() pour eliminer
la confusion VIP/Lost identifiee lors des tests de validation.

Seuils de segmentation bases sur les medianes du dataset Olist (96 476 commandes) :
    SEUIL_RISK  = 0.50  (mediane risk_proba)
    SEUIL_PRICE = 150.0 (mediane total_items_price en R$)
"""

import logging
import pathlib
from datetime import datetime, timezone
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger("scoring_pipeline")

SEUIL_RISK  = 0.50
SEUIL_PRICE = 150.0


class ScoringPipeline:
    """Charge les artefacts ML et execute le scoring en cascade M1->M2->Regle."""

    FEATURES_M1: List[str] = [
        "distance_km", "total_freight", "order_month", "order_day_of_week"
    ]
    # Ordre exact valide par XGBoost feature_names_in_ — NE PAS MODIFIER
    FEATURES_M2: List[str] = [
        "predicted_delay", "total_items_price", "review_score"
    ]
    FEATURES_M3: List[str] = [
        "risk_proba", "total_items_price", "nb_items"
    ]

    def __init__(self, models_path: str = "models") -> None:
        self._base = pathlib.Path(models_path)
        self.m1: Any             = None
        self.m2: Any             = None
        self.m3: Any             = None
        self.scaler: Any         = None
        self.segment_map: Dict[int, str] = {}
        self._load_models()

    def _load_models(self) -> None:
        """Charge les 5 fichiers pkl depuis le disque."""
        for attr, filename in [
            ("m1",          "model1_delay.pkl"),
            ("m2",          "model2_risk.pkl"),
            ("m3",          "model3_segment.pkl"),
            ("scaler",      "scaler3.pkl"),
            ("segment_map", "segment_map.pkl"),
        ]:
            path = self._base / filename
            try:
                setattr(self, attr, joblib.load(path))
                logger.info("%s charge depuis %s", filename, path)
            except Exception as exc:
                raise RuntimeError(
                    f"Impossible de charger {filename} : {exc}"
                ) from exc

        logger.info("Segment map charge : %s", self.segment_map)
        logger.info(
            "Scaler features : %s",
            list(getattr(self.scaler, "feature_names_in_", []))
        )

    @staticmethod
    def _segment_rule(risk_proba: float, total_items_price: float) -> str:
        """
        Regle de segmentation deterministe.

        Matrice de decision :
            risk < 0.50  AND price >= 150  -> VIP
            risk < 0.50  AND price <  150  -> Loyal
            risk >= 0.50 AND price >= 150  -> At Risk
            risk >= 0.50 AND price <  150  -> Lost
        """
        if risk_proba < SEUIL_RISK and total_items_price >= SEUIL_PRICE:
            return "VIP"
        if risk_proba < SEUIL_RISK and total_items_price < SEUIL_PRICE:
            return "Loyal"
        if risk_proba >= SEUIL_RISK and total_items_price >= SEUIL_PRICE:
            return "At Risk"
        return "Lost"

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Execute la cascade M1 -> M2 -> Regle sur une observation unique."""

        # M1 — Prediction du delai de livraison
        try:
            m1_input = pd.DataFrame(
                [{k: features[k] for k in self.FEATURES_M1}]
            )
            predicted_delay: float = float(self.m1.predict(m1_input)[0])
        except KeyError as exc:
            raise ValueError(f"Feature manquante pour M1 : {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Erreur M1 : {exc}") from exc

        # M2 — Scoring du risque NPS
        try:
            m2_input = pd.DataFrame(
                [[predicted_delay,
                  features["total_items_price"],
                  features["review_score"]]],
                columns=self.FEATURES_M2
            )
            risk_proba: float = float(self.m2.predict_proba(m2_input)[0, 1])
            risk_label: int   = int(risk_proba >= 0.5)
        except KeyError as exc:
            raise ValueError(f"Feature manquante pour M2 : {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Erreur M2 : {exc}") from exc

        # M3 — Segmentation par regle deterministe
        try:
            segment: str = self._segment_rule(
                risk_proba,
                features["total_items_price"]
            )
        except Exception as exc:
            raise RuntimeError(f"Erreur regle segmentation : {exc}") from exc

        if risk_proba < 0.35:
            risk_level = "Low"
        elif risk_proba < 0.65:
            risk_level = "Medium"
        else:
            risk_level = "High"

        return {
            "predicted_delay_days" : round(predicted_delay, 2),
            "risk_proba"           : round(risk_proba, 4),
            "risk_label"           : risk_label,
            "risk_level"           : risk_level,
            "segment"              : segment,
            "confidence_score"     : round(max(risk_proba, 1 - risk_proba), 4),
            "scored_at"            : datetime.now(timezone.utc).isoformat(),
        }

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Score un DataFrame complet de maniere vectorisee (scoring Airflow)."""
        if df.empty:
            return df

        all_features = self.FEATURES_M1 + ["review_score", "total_items_price", "nb_items"]
        id_cols      = [c for c in ["order_key"] if c in df.columns]
        df           = df[id_cols + all_features].copy()
        df[all_features] = df[all_features].apply(
            pd.to_numeric, errors="coerce"
        ).fillna(0)

        # M1 — Prediction vectorisee du delai
        df["predicted_delay_days"] = self.m1.predict(df[self.FEATURES_M1]).round(2)
        df["predicted_delay"]      = df["predicted_delay_days"]

        # M2 — Scoring vectorise du risque
        m2_input    = df[self.FEATURES_M2]
        risk_probas = self.m2.predict_proba(m2_input)[:, 1]
        df["risk_proba"] = risk_probas.round(4)
        df["risk_label"] = (risk_probas >= 0.5).astype(int)
        df["risk_level"] = np.select(
            [df["risk_proba"] < 0.35, df["risk_proba"] < 0.65],
            ["Low", "Medium"],
            default="High"
        )

        # M3 — Regle deterministe vectorisee
        df["segment"] = df.apply(
            lambda row: self._segment_rule(
                row["risk_proba"],
                row["total_items_price"]
            ),
            axis=1
        )

        df["confidence_score"] = np.maximum(
            df["risk_proba"], 1 - df["risk_proba"]
        ).round(4)
        df["scored_at"] = datetime.now(timezone.utc).isoformat()

        return df


def run_batch_scoring() -> None:
    """
    Fonction principale pour Airflow ou execution manuelle.
    Flux : DuckDB (mart_ml_prediction_master) -> Scoring -> PostgreSQL (quality.ml_predictions)
    """
    import os
    import duckdb
    from dotenv import load_dotenv
    load_dotenv()

    logger.info("Initialisation du pipeline de scoring...")
    pipeline = ScoringPipeline("models")

    db_path = os.getenv("DUCKDB_DATABASE_PATH", "data/processed/warehouse.duckdb")
    logger.info("Lecture depuis DuckDB : %s", db_path)

    con_duck = duckdb.connect(database=db_path, read_only=True)
    df       = con_duck.execute(
        "SELECT * FROM main.mart_ml_prediction_master"
    ).df()
    con_duck.close()

    if df.empty:
        logger.warning("Aucune donnee trouvee dans DuckDB.")
        return

    logger.info("Scoring de %d lignes en cascade...", len(df))
    df_scored = pipeline.predict_batch(df)

    host     = os.getenv("POSTGRES_DWH_HOST",     "127.0.0.1")
    port     = os.getenv("POSTGRES_DWH_PORT",     "5433")
    user     = os.getenv("POSTGRES_DWH_USER",     "admin")
    password = os.getenv("POSTGRES_DWH_PASSWORD", "admin")
    dbname   = os.getenv("POSTGRES_DWH_DB",       "dwh_db")

    import psycopg2
    from psycopg2 import sql as pg_sql

    cols_to_keep = ["order_key", "predicted_delay_days", "risk_proba",
                    "risk_level", "segment", "scored_at"]
    final_df = df_scored[[c for c in cols_to_keep if c in df_scored.columns]]

    conn = psycopg2.connect(host=host, port=int(port), user=user,
                            password=password, dbname=dbname)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DROP TABLE IF EXISTS quality.ml_predictions;
                CREATE TABLE quality.ml_predictions (
                    order_key             TEXT,
                    predicted_delay_days  FLOAT,
                    risk_proba            FLOAT,
                    risk_level            TEXT,
                    segment               TEXT,
                    scored_at             TEXT
                );
            """)
            rows = [tuple(r) for r in final_df.itertuples(index=False)]
            cur.executemany(
                "INSERT INTO quality.ml_predictions VALUES (%s,%s,%s,%s,%s,%s)",
                rows
            )
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "Table quality.ml_predictions mise a jour : %d lignes.", len(final_df)
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_batch_scoring()
