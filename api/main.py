"""
FastAPI backend pour la plateforme E-Commerce Intelligence.

Endpoints existants :
    GET  /health          — healthcheck general
    GET  /products        — catalogue produit pagine
    GET  /sellers         — referentiel vendeurs pagine

Endpoints ML (ajoutes) :
    POST /predict         — scoring en cascade d'une commande
    GET  /predict/health  — etat de sante des modeles ML
    GET  /predict/segments/stats — distribution des segments depuis PostgreSQL
    POST /recommend       — recommandations IA via Mistral 7B (OpenRouter)
"""

import math
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ajouter la racine du projet au path pour importer scoring_pipeline
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ml.scoring_pipeline import ScoringPipeline
from ai_recommender import get_ai_recommendations

# ------------------------------------------------------------------
# Lifespan : chargement unique des modeles au demarrage
# ------------------------------------------------------------------
pipeline: Optional[ScoringPipeline] = None


@asynccontextmanager
async def lifespan(application: FastAPI):
    global pipeline
    models_dir = os.getenv("MODELS_DIR", os.path.join(os.path.dirname(__file__), "..", "models"))
    try:
        pipeline = ScoringPipeline(models_dir)
    except Exception as exc:
        print(f"WARN: Impossible de charger les modeles ML : {exc}")
        pipeline = None
    yield
    pipeline = None


# ------------------------------------------------------------------
# Application FastAPI
# ------------------------------------------------------------------
app = FastAPI(
    title="E-Commerce Intelligence API",
    description="API pour l'exposition des donnees et le scoring ML en cascade.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Schemas Pydantic — ML
# ------------------------------------------------------------------


class PredictRequest(BaseModel):
    distance_km: float = Field(
        ..., ge=0.0, le=20000.0,
        description="Distance client-vendeur en kilometres",
        json_schema_extra={"example": 450.0},
    )
    total_freight: float = Field(
        ..., ge=0.0, le=2000.0,
        description="Frais de livraison en BRL",
        json_schema_extra={"example": 25.50},
    )
    order_month: int = Field(
        ..., ge=1, le=12,
        description="Mois de la commande (1=Janvier, 12=Decembre)",
        json_schema_extra={"example": 6},
    )
    order_day_of_week: int = Field(
        ..., ge=0, le=6,
        description="Jour de la semaine (0=Lundi, 6=Dimanche)",
        json_schema_extra={"example": 2},
    )
    review_score: float = Field(
        ..., ge=1.0, le=5.0,
        description="Score de satisfaction client (1 a 5)",
        json_schema_extra={"example": 4.0},
    )
    total_items_price: float = Field(
        ..., ge=0.0, le=15000.0,
        description="Montant total des articles en BRL",
        json_schema_extra={"example": 185.90},
    )
    nb_items: int = Field(
        ..., ge=1, le=50,
        description="Nombre d'articles dans la commande",
        json_schema_extra={"example": 2},
    )


class PredictResponse(BaseModel):
    predicted_delay_days: float
    risk_proba: float
    risk_label: int
    risk_level: str
    segment: str
    confidence_score: float
    scored_at: str


# ------------------------------------------------------------------
# Endpoints existants (inchanges)
# ------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.csv")
SELLERS_FILE = os.path.join(DATA_DIR, "sellers.csv")


def get_paginated_data(filepath: str, page: int, size: int):
    if not os.path.exists(filepath):
        return {"status": "error", "message": "Fichier de donnees introuvable."}

    df = pd.read_csv(filepath)
    df = df.astype(object).where(pd.notnull(df), None)

    total_records = len(df)
    total_pages = math.ceil(total_records / size)

    start_idx = (page - 1) * size
    end_idx = start_idx + size
    page_df = df.iloc[start_idx:end_idx]

    return {
        "status": "success",
        "page": page,
        "size": size,
        "total_records": total_records,
        "total_pages": total_pages,
        "data": page_df.to_dict(orient="records"),
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/products")
def get_products(page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=1000)):
    """Endpoint pour recuperer le catalogue produit avec pagination"""
    return get_paginated_data(PRODUCTS_FILE, page, size)


@app.get("/sellers")
def get_sellers(page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=1000)):
    """Endpoint pour recuperer le referentiel des vendeurs avec pagination"""
    return get_paginated_data(SELLERS_FILE, page, size)


# ------------------------------------------------------------------
# Endpoints ML
# ------------------------------------------------------------------


@app.post("/predict", response_model=PredictResponse)
def predict_order(request: PredictRequest):
    """Score une commande via la cascade M1 -> M2 -> M3."""
    if pipeline is None:
        raise HTTPException(status_code=500, detail="Modeles ML non charges.")
    try:
        result = pipeline.predict(request.model_dump())
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {exc}") from exc


@app.get("/predict/health")
def predict_health():
    """Retourne l'etat de sante du pipeline ML."""
    return {
        "status": "ok" if pipeline is not None else "unavailable",
        "models_loaded": pipeline is not None,
        "model_versions": {
            "m1": "lightgbm",
            "m2": "xgboost",
            "m3": "kmeans",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/predict/segments/stats")
def predict_segments_stats():
    """Retourne la distribution des segments depuis PostgreSQL."""
    host = os.getenv("POSTGRES_DWH_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_DWH_PORT", "5433")
    user = os.getenv("POSTGRES_DWH_USER", "admin")
    password = os.getenv("POSTGRES_DWH_PASSWORD", "admin")
    dbname = os.getenv("POSTGRES_DWH_DB", "dwh_db")

    try:
        from sqlalchemy import create_engine, text

        db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        engine = create_engine(db_url)

        with engine.connect() as conn:
            # Distribution des segments
            dist_query = text(
                "SELECT segment, COUNT(*) as count "
                "FROM quality.ml_predictions "
                "GROUP BY segment ORDER BY count DESC"
            )
            dist_rows = conn.execute(dist_query).fetchall()
            distribution = {row[0]: row[1] for row in dist_rows}

            # 10 dernieres predictions
            recent_query = text(
                "SELECT order_key, predicted_delay_days, risk_proba, segment "
                "FROM quality.ml_predictions "
                "ORDER BY order_key DESC LIMIT 10"
            )
            recent_rows = conn.execute(recent_query).fetchall()
            recent = [
                {
                    "order_key": r[0],
                    "predicted_delay_days": round(float(r[1]), 2) if r[1] else None,
                    "risk_proba": round(float(r[2]), 4) if r[2] else None,
                    "segment": r[3],
                }
                for r in recent_rows
            ]

        return {"distribution": distribution, "recent_predictions": recent}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur PostgreSQL : {exc}") from exc


# ------------------------------------------------------------------
# Endpoint IA — Recommandations Mistral 7B via OpenRouter
# ------------------------------------------------------------------

class RecommendRequest(BaseModel):
    predicted_delay_days: float = Field(..., description="Delai predit en jours")
    risk_proba: float           = Field(..., description="Probabilite de risque [0,1]")
    segment: str                = Field(..., description="Segment client: VIP, Loyal, At Risk, Lost")
    distance_km: float          = Field(0.0)
    total_items_price: float    = Field(0.0)
    review_score: float         = Field(3.0)
    order_month: int            = Field(6)


@app.post("/recommend")
async def recommend(request: RecommendRequest):
    """Genere 3 recommandations contextuelles via Mistral 7B (OpenRouter).
    Retourne le fallback statique en cas d'erreur ou si la cle API est absente."""
    scoring_context = request.model_dump()
    recommendations = await get_ai_recommendations(scoring_context)
    return {"recommendations": recommendations}
