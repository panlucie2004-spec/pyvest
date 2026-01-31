# Fichier: src/pyvest/loader.py

from pathlib import Path
import logging
import pickle
from datetime import datetime
from typing import Sequence

import pandas as pd
import yfinance as yf

from priceseries import PriceSeries

class DataLoader:
    """
    Charge des données de marché depuis Yahoo Finance avec un système de cache.
    
    Le système de cache gère cinq scénarios de correspondance temporelle :
    1. EXACT : La requête correspond exactement aux données en cache
    2. CONTAINS : La requête est un sous-ensemble du cache
    3. OVERLAP_AFTER : Intersection partielle, fetch complémentaire à droite
    4. OVERLAP_BEFORE : Intersection partielle, fetch complémentaire à gauche
    5. MISS : Aucune donnée en cache, fetch complet nécessaire
    
    Attributes:
        cache_dir: Répertoire de stockage du cache
        logger: Logger pour le suivi des opérations
    """
    
    def __init__(self, cache_dir: str = ".cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_cache_path(
        self, 
        ticker: str, 
        price_col: str, 
        dates: tuple[str, str]
    ) -> Path:
        """
        Génère le chemin du fichier cache pour une requête donnée.
        
        Format: {ticker}_{price_col}_{start}_{end}.pkl
        """
        return self.cache_dir / f"{ticker}_{price_col}_{dates[0]}_{dates[1]}.pkl"

    def _check_date_overlap(
        self,
        cached_start: pd.Timestamp,
        cached_end: pd.Timestamp,
        req_start: pd.Timestamp,
        req_end: pd.Timestamp
    ) -> tuple[str, pd.Timestamp | None, pd.Timestamp | None]:
        """
        Détermine le type de chevauchement entre le cache et la requête
        
        Returns:
            tuple: (status, gap_start, gap_end)
            - status: "exact" | "contains" | "overlap_before" | "overlap_after" | "miss"
            - gap_start: Début de la période manquante (si overlap)
            - gap_end: Fin de la période manquante (si overlap)
        """
        # Cas MISS: Aucune intersection
        if cached_end < req_start or cached_start > req_end:
            return ("miss", None, None)

        # Cas exact: hit parfait du cache
        if cached_start == req_start and cached_end == req_end:
            return ("exact", None, None)

        # Cas CONTAINS: hit du cache qui contient complétement la requête
        if cached_start <= req_start and cached_end >= req_end:
            return ("contains", None, None)

        # Cas OVERLAP_AFTER: cache hit mais la requête déborde à droite
        if cached_start <= req_start and cached_end < req_end:
            gap_start = cached_end + pd.Timedelta(days=1)
            gap_end = req_end
            return ("overlap_after", gap_start, gap_end)

        # Cas OVERLAP_BEFORE: cache hit mais la requête déborde à gauche
        if cached_start > req_start and cached_end >= req_end:
            gap_start = req_start
            gap_end = cached_start - pd.Timedelta(days=1)
            return ("overlap_before", gap_start, gap_end)
        
        return ("miss", None, None)

    def _load_from_cache(
        self,
        ticker: str,
        price_col: str,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp
    ) -> tuple[pd.DataFrame | None, str, tuple | None]:
        """
        Recherche et charge les données disponibles en cache.
        """
        if not self.cache_dir.exists():
            return (None, "miss", None)

        for file_path in self.cache_dir.iterdir():
            if not file_path.is_file() or file_path.suffix != '.pkl':
                continue

            try:
                name_parts = file_path.stem.split('_')
                if len(name_parts) < 4:
                    continue
                
                if name_parts[0] != ticker or name_parts[1] != price_col:
                    continue

                cached_start = pd.to_datetime(name_parts[2])
                cached_end = pd.to_datetime(name_parts[3])

                status, gap_start, gap_end = self._check_date_overlap(
                    cached_start, cached_end, start_date, end_date
                )

                if status != "miss":
                    with open(file_path, 'rb') as f:
                        data = pickle.load(f)

                    df = pd.DataFrame({price_col: data['prices']})
                    df.index = pd.to_datetime(data['dates'])

                    return (df, status, (gap_start, gap_end))

            except Exception as e:
                self.logger.warning(f"Fichier cache corrompu {file_path}: {e}")
                continue

        return (None, "miss", None)
    
    def _save_to_cache(
        self, 
        cache_path: Path, 
        prices: list[float],
        dates: list,
        ticker: str, 
        start: str, 
        end: str
    ) -> None:
        """ Sauvegarde les prix dans un fichier cache avec metadata """
        data = {
            "ticker": ticker, "start": start, "end": end,
            "fetched_at": datetime.now().isoformat(),
            "prices": prices, "dates": dates
        }
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)

    def fetch_single_ticker(
        self, 
        ticker: str, 
        price_col: str, 
        dates: tuple[str, str]
    ) -> PriceSeries | None:
        """
        Récupère les données de prix d'un ticker unique avec système de cache.
        """
        start_ts, end_ts = pd.to_datetime(dates[0]), pd.to_datetime(dates[1])
        cached_df, status, gap_range = self._load_from_cache(ticker, price_col, start_ts, end_ts)

        # 1 & 2. Cas EXACT ou CONTAINS : On utilise le cache
        if status in ["exact", "contains"]:
            self.logger.info(f"Cache HIT ({status}) pour {ticker}")
            final_df = cached_df.loc[start_ts:end_ts]
        
        # 3 & 4. Cas OVERLAP : Fetch la partie manquante et fusionner
        elif status.startswith("overlap"):
            gap_start, gap_end = gap_range
            self.logger.info(f"Cache PARTIAL ({status}) pour {ticker}. Gap: {gap_start} -> {gap_end}")
            
            new_data = yf.download(ticker, start=gap_start, end=gap_end, progress=False)
            if new_data.empty:
                final_df = cached_df
            else:
                new_df = new_data[[price_col]]
                final_df = pd.concat([cached_df, new_df]).sort_index()
                # Supprimer les doublons et trier par date
                final_df = final_df[~final_df.index.duplicated(keep='first')]
                
                # Sauvegarde du cache étendu
                new_start = final_df.index.min().strftime('%Y-%m-%d')
                new_end = final_df.index.max().strftime('%Y-%m-%d')
                new_path = self._get_cache_path(ticker, price_col, (new_start, new_end))
                self._save_to_cache(new_path, final_df[price_col].tolist(), 
                                   final_df.index.strftime('%Y-%m-%d').tolist(), 
                                   ticker, new_start, new_end)
        
        # 5. Cas MISS : Fetch complet
        else:
            self.logger.info(f"Cache MISS pour {ticker}. Fetching all.")
            data = yf.download(ticker, start=dates[0], end=dates[1], progress=False)
            if data.empty: return None
            
            final_df = data[[price_col]]
            self._save_to_cache(self._get_cache_path(ticker, price_col, dates), 
                               final_df[price_col].tolist(), 
                               final_df.index.strftime('%Y-%m-%d').tolist(), 
                               ticker, dates[0], dates[1])

        return PriceSeries(ticker, final_df[price_col])

    def fetch_multiple_tickers(
        self,
        tickers: Sequence[str],
        price_col: str,
        dates: tuple[str, str]
    ) -> dict[str, PriceSeries]:
        """
        Récupère les données de prix pour plusieurs tickers.
        """
        results = {}
        for ticker in tickers:
            ps = self.fetch_single_ticker(ticker, price_col, dates)
            if ps is not None:
                results[ticker] = ps
        return results
    
    def clear_cache(self) -> int:
        """
        Supprime tous les fichiers du cache.
        
        Returns:
            Nombre de fichiers supprimés
        """
        count = 0
        for file_path in self.cache_dir.glob("*.pkl"):
            file_path.unlink()
            count += 1
        self.logger.info(f"Cache vidé: {count} fichiers supprimés.")
        return count