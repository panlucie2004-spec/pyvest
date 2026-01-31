

from .asset import Asset
from typing import Iterator
from itertools import combinations
import pandas as pd
import numpy as np



class Universe:
    """
    Collection d'actifs représentant un univers d'investissement.
    
    Pattern de conception : AGRÉGATION
    ──────────────────────────────────
    Universe CONTIENT des Asset, mais les Asset peuvent exister 
    indépendamment de l'Universe.
    """
    
    def __init__(self, assets: list[Asset] | None = None) -> None:
        self._assets: dict[str, Asset] = {}
        if assets:
            for asset in assets:
                self.add(asset)
    
    def add(self, asset: Asset) -> None:
        """Ajoute un actif à l'univers en utilisant son ticker comme clé."""
        self._assets[asset.ticker] = asset
    
    def get(self, ticker: str) -> Asset | None:
        """Récupère un actif par son ticker. Retourne None s'il n'existe pas."""
        return self._assets.get(ticker)
    
    def remove(self, ticker: str) -> Asset | None:
        """Retire et retourne l'actif de l'univers."""
        return self._assets.pop(ticker, None)
    
    def __len__(self) -> int:
        """Retourne le nombre d'actifs dans l'univers."""
        return len(self._assets)
    
    def __iter__(self) -> Iterator[Asset]:
        """Permet d'itérer directement sur les objets Asset de l'univers."""
        return iter(self._assets.values())
    
    def __contains__(self, ticker: str) -> bool:
        """Permet de vérifier la présence d'un ticker avec l'opérateur 'in'."""
        return ticker in self._assets
    
    @property
    def tickers(self) -> list[str]:
        """Liste de tous les tickers présents dans l'univers."""
        return list(self._assets.keys())
    
    def filter_by_sector(self, sector: str) -> list[Asset]:
        """Filtre les actifs par secteur (insensible à la casse)."""
        return [
            asset for asset in self._assets.values() 
            if asset.sector.lower() == sector.lower()
        ]
    
    def top_k_correlations(
        assets: list[Asset],
        k: int = 20,
        use_absolute: bool = False
    ) -> list[tuple[str, str, float]]:
        """
        Extrait les K paires les plus corrélées d'une liste d'actifs.
        """
        correlations = []
    
        for asset_1, asset_2 in combinations(assets, 2):
            # On suppose que Asset a une méthode .correlation_with(other_asset)
            # ou un accès à ses rendements historiques pour calculer Pearson
            rho = asset_1.correlation_with(asset_2)
        
            correlations.append((asset_1.ticker, asset_2.ticker, rho))
    
        # Définition de la clé de tri
        # Si use_absolute est True, on trie par |rho|, sinon par rho
        sort_key = lambda x: abs(x[2]) if use_absolute else x[2]
    
        # Tri décroissant (reverse=True) pour avoir les plus fortes corrélations en premier
        correlations.sort(key=sort_key, reverse=True)
    
        return correlations[:k]
    
    def build_correlation_matrix(assets: list[Asset]) -> pd.DataFrame:
        """
        Construit une matrice de corrélation symétrique pour tous les actifs.
        """
        tickers = [a.ticker for a in assets]
        n = len(tickers)
    
        matrix = np.full((n, n), np.nan)
        np.fill_diagonal(matrix, 1.0)
    
        ticker_to_idx = {t: i for i, t in enumerate(tickers)}
    
        # Remplir le triangle supérieur et inférieur (symétrie)
        for asset_1, asset_2 in combinations(assets, 2):
            i, j = ticker_to_idx[asset_1.ticker], ticker_to_idx[asset_2.ticker]
            rho = asset_1.correlation_with(asset_2)
        
            matrix[i, j] = rho
            matrix[j, i] = rho  # Propriété de symétrie : corr(A, B) = corr(B, A)
    
        return pd.DataFrame(matrix, index=tickers, columns=tickers)


    def extract_upper_triangle(corr_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        Extrait les paires uniques du triangle supérieur de la matrice.
        """
        # Créer un masque pour le triangle supérieur (excluant la diagonale k=1)
        # k=1 signifie qu'on commence juste au-dessus de la diagonale principale
        mask = np.triu(np.ones(corr_matrix.shape, dtype=bool), k=1)
    
        # On applique le masque et on transforme la matrice en série (index_1, index_2, valeur)
        # .where(mask) garde les valeurs du triangle sup et met le reste à NaN
        # .stack() supprime les NaN par défaut, ne laissant que les paires uniques
        pairs = corr_matrix.where(mask).stack().reset_index()
    
        # Renommer les colonnes pour la clarté
        pairs.columns = ['asset_1', 'asset_2', 'correlation']
    
        # Trier par corrélation décroissante
        return pairs.sort_values(by='correlation', ascending=False).reset_index(drop=True)