
from asset import Asset
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
        if not isinstance(asset, Asset):
            raise TypeError("L'objet doit être une instance de la classe Asset.")
        self._assets[asset.ticker] = asset
    
    def get(self, ticker: str) -> Asset | None:
        """Récupère un actif par son ticker. Retourne None s'il n'existe pas."""
        return self._assets.get(ticker)
    
    def remove(self, ticker: str) -> Asset | None:
        """Retire un actif de l'univers et le retourne."""
        return self._assets.pop(ticker, None)
    
    def __len__(self) -> int:
        """Retourne le nombre d'actifs dans l'univers."""
        return len(self._assets)
    
    def __iter__(self) -> Iterator[Asset]:
        """Permet d'itérer directement sur les objets Asset de l'univers."""
        return iter(self._assets.values())
    
    def __contains__(self, ticker: str) -> bool:
        """Permet d'utiliser la syntaxe 'AAPL' in universe."""
        return ticker in self._assets
    
    @property
    def tickers(self) -> list[str]:
        """Retourne la liste de tous les tickers présents dans l'univers."""
        return list(self._assets.keys())
    
    def filter_by_sector(self, sector: str) -> list[Asset]:
        """Filtre les actifs par secteur (insensible à la casse)."""
        return [
            asset for asset in self._assets.values() 
            if getattr(asset, 'sector', '').lower() == sector.lower()
        ]

    def top_k_correlations(
        self,
        k: int = 20,
        use_absolute: bool = False
    ) -> list[tuple[str, str, float]]:
        """
        Extrait les K paires les plus corrélées d'une liste d'actifs.
        """
        correlations = []
    
        # itertools.combinations génère toutes les paires uniques
        # évitant les doublons (A,B) et (B,A) et les auto-corrélations (A,A)
        # On utilise les actifs présents dans l'univers actuel
        for asset_1, asset_2 in combinations(self._assets.values(), 2):
            # Calcul de la corrélation de Pearson entre les deux séries de rendements
            # On utilise généralement pandas pour la méthode .corr()
            corr_value = asset_1.returns.corr(asset_2.returns)
        
            # On ignore les valeurs NaN (si une série est vide ou constante)
            if not pd.isna(corr_value):
                correlations.append((asset_1.ticker, asset_2.ticker, corr_value))
    
        # Trier par corrélation (ou valeur absolue) et retourner les k premières
        # Si use_absolute est True, on trie par la valeur absolue |rho|
        correlations.sort(
            key=lambda x: abs(x[2]) if use_absolute else x[2], 
            reverse=True
        )
    
        return correlations[:k]
    
    def build_correlation_matrix(assets: list[Asset]) -> pd.DataFrame:
        """
        Construit une matrice de corrélation pour tous les actifs.
    
        Returns:
            DataFrame symétrique avec tickers en index et colonnes
        """
        tickers = [a.ticker for a in assets]
        n = len(tickers)
    
        # Initialiser la matrice avec NaN
        matrix = np.full((n, n), np.nan)
    
        # Pre-remplir la diagonale avec 1.0
        np.fill_diagonal(matrix, 1.0)
    
        # Créer un mapping ticker -> index pour un accès rapide O(1)
        ticker_to_idx = {t: i for i, t in enumerate(tickers)}
    
        # Remplir le triangle supérieur et inférieur (symétrie)
        # itertools.combinations génère les paires uniques (A, B)
        for asset_1, asset_2 in combinations(assets, 2):
            # Calcul de la corrélation entre les deux actifs
            corr_value = asset_1.returns.corr(asset_2.returns)
        
            # Récupération des indices via le mapping
            i, j = ticker_to_idx[asset_1.ticker], ticker_to_idx[asset_2.ticker]
        
            # Application de la symétrie : la corrélation (i, j) est égale à (j, i)
            matrix[i, j] = corr_value
            matrix[j, i] = corr_value
    
        return pd.DataFrame(matrix, index=tickers, columns=tickers)


    def extract_upper_triangle(corr_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        Extrait les paires uniques du triangle supérieur de la matrice.
    
        Utile pour éviter les doublons (AAPL-MSFT et MSFT-AAPL) et
        exclure la diagonale (auto-corrélations).
    
        Cette méthode est similaire à celle utilisée dans le projet
        "Global Multi-Asset Correlation Lab".
    
        Args:
            corr_matrix: Matrice de corrélation (DataFrame carré)
    
        Returns:
            DataFrame avec colonnes ['asset_1', 'asset_2', 'correlation']
            trié par corrélation décroissante
        """
        # Créer un masque pour le triangle supérieur (excluant la diagonale k=1)
        mask = np.triu(np.ones(corr_matrix.shape, dtype=bool), k=1)
    
        # Application du masque et transformation de la matrice en format long (stack)
        # On ne garde que les valeurs du triangle supérieur
        pairs = corr_matrix.where(mask).stack().reset_index()
    
        # Renommer les colonnes pour correspondre au format attendu
        pairs.columns = ['asset_1', 'asset_2', 'correlation']
    
        # Trier par corrélation décroissante
        return pairs.sort_values(by='correlation', ascending=False).reset_index(drop=True)