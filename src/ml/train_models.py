import pandas as pd
import joblib
import os
from lightgbm import LGBMRegressor
from xgboost import XGBClassifier
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split

def train_cascade_pipeline():
    # 1. Chargement des données
    csv_path = "data/ml_features.csv"
    if not os.path.exists(csv_path):
        print(f"❌ Erreur : Fichier {csv_path} introuvable. Lancez d'abord export_for_ml.py.")
        return

    df = pd.read_csv(csv_path)
    print(f"INFO: Donnees chargees : {df.shape}")

    # Créer le dossier models s'il n'existe pas
    os.makedirs("models", exist_ok=True)

    # ------------------------------------------------------------------------------
    # M1 : DÉLAI DE LIVRAISON (Régression)
    # ------------------------------------------------------------------------------
    print("\n[1/3] Entrainement Modele 1 (Delai)...")
    f1 = ['distance_km', 'total_freight', 'order_month', 'order_day_of_week']
    X1 = df[f1].fillna(0)
    y1 = df['delivery_days'].fillna(df['delivery_days'].mean())

    m1 = LGBMRegressor(n_estimators=100, learning_rate=0.05, verbose=-1)
    m1.fit(X1, y1)
    joblib.dump(m1, "models/model1_delay.pkl")
    print("SUCCESS: M1 sauvegarde dans models/model1_delay.pkl")

    # ------------------------------------------------------------------------------
    # M2 : RISQUE DE CHURN (Classification)
    # ------------------------------------------------------------------------------
    print("\n[2/3] Entrainement Modele 2 (Churn)...")
    # On enrichit avec la prédiction de M1
    df['predicted_delay'] = m1.predict(X1)
    
    f2 = ['predicted_delay', 'total_items_price', 'review_score']
    X2 = df[f2].fillna(0)
    y2 = df['is_late'].astype(int)

    m2 = XGBClassifier(n_estimators=100, verbosity=0)
    m2.fit(X2, y2)
    joblib.dump(m2, "models/model2_churn.pkl")
    print("SUCCESS: M2 sauvegarde dans models/model2_churn.pkl")

    # ------------------------------------------------------------------------------
    # M3 : SEGMENTATION (Clustering)
    # ------------------------------------------------------------------------------
    print("\n[3/3] Entrainement Modele 3 (Segments)...")
    # On enrichit avec la probabilité de churn de M2
    df['churn_proba'] = m2.predict_proba(X2)[:, 1]

    f3 = ['churn_proba', 'total_items_price', 'nb_items']
    X3 = df[f3].fillna(0)

    m3 = KMeans(n_clusters=4, random_state=42, n_init=10)
    m3.fit(X3)
    joblib.dump(m3, "models/model3_segment.pkl")
    print("SUCCESS: M3 sauvegarde dans models/model3_segment.pkl")

    print("\nDONE: PIPELINE ML COMPLET GENERE AVEC SUCCES !")

if __name__ == "__main__":
    train_cascade_pipeline()
