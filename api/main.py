from fastapi import FastAPI, Query
from typing import List, Optional
import pandas as pd
import math
import os

app = FastAPI(
    title="E-Commerce REST API Mock",
    description="API mock pour exposer les données products et sellers du dataset e-commerce."
)

# Chemins des fichiers CSV
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.csv")
SELLERS_FILE = os.path.join(DATA_DIR, "sellers.csv")

def get_paginated_data(filepath: str, page: int, size: int):
    if not os.path.exists(filepath):
        return {"status": "error", "message": "Fichier de données introuvable."}
    
    # Lecture du CSV avec Pandas (remarque : en prod, on utiliserait une BDD)
    df = pd.read_csv(filepath)
    # Remplacer les valeurs NaN par None pour compatibilité JSON
    df = df.astype(object).where(pd.notnull(df), None)
    
    total_records = len(df)
    total_pages = math.ceil(total_records / size)
    
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    
    # Extraire la page
    page_df = df.iloc[start_idx:end_idx]
    
    return {
        "status": "success",
        "page": page,
        "size": size,
        "total_records": total_records,
        "total_pages": total_pages,
        "data": page_df.to_dict(orient="records")
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/products")
def get_products(page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=1000)):
    """Endpoint pour récupérer le catalogue produit avec pagination"""
    return get_paginated_data(PRODUCTS_FILE, page, size)

@app.get("/sellers")
def get_sellers(page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=1000)):
    """Endpoint pour récupérer le référentiel des vendeurs avec pagination"""
    return get_paginated_data(SELLERS_FILE, page, size)
