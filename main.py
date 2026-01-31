import sys
import os

# Ajoute le dossier 'src' au chemin de recherche
sys.path.append(os.path.abspath("src"))

from pyvest.asset import Asset
from pyvest.priceseries import PriceSeries

# Test rapide
prices = PriceSeries([100.0, 105.0, 102.0], name="Test")
apple = Asset(ticker="AAPL", prices=prices)

print(f"✅ Succès ! L'actif {apple.ticker} est chargé à {apple.current_price}$")