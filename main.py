import sys
import os
import pandas as pd

# 1. Configuration du chemin
sys.path.append(os.path.abspath("src"))

# 2. Imports officiels
from pyvest.asset import Asset
from pyvest.universe import Universe
from pyvest.priceseries import PriceSeries
from pyvest.constant import CurrencyEnum 

# Simulation de Sectors (à ajouter dans constant.py plus tard)
class Sectors:
    TECH = "Technology"

# 3. Simulation des données
data = {
    "Date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
    "AAPL": [150.0, 155.0, 152.0],
    "MSFT": [280.0, 285.0, 282.0]
}
df_prices = pd.DataFrame(data).set_index("Date")

# 4. Création des actifs
assets_list = []
for ticker in df_prices.columns:
    # --- LA CORRECTION EST ICI ---
    # Signature attendue par ton fichier : (values: list, name: str)
    # On passe donc : (les prix, le nom)
    ps = PriceSeries(df_prices[ticker].tolist(), ticker)
    
    # Asset attend : (ticker: str, prices: PriceSeries, sector: str)
    new_asset = Asset(ticker, ps, sector=Sectors.TECH)
    assets_list.append(new_asset)

# 5. Initialisation de l'Univers
universe = Universe(assets_list)

print(f"--- Rapport d'Univers ({len(universe)} actifs) ---")

# Utilisation de ton itérateur et de ta propriété @property current_price
for asset in universe: 
    print(f"✅ {asset.ticker} ({asset.sector}) : {asset.current_price:.2f}$")

# 6. Test du filtrage
tech_assets = universe.filter_by_sector(Sectors.TECH)
print(f"\nActifs filtrés dans le secteur {Sectors.TECH} : {len(tech_assets)}")