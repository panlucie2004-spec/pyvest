# Fichier: pyvest/src/loader.py


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

        # Cas OVERLAP_AFTER: cache hit mais la requête débordre à droite
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
        
        Parcourt les fichiers du répertoire cache pour trouver une correspondance
        avec le couple (ticker, price_col) et détermine le type de chevauchement.
        
        Args:
            ticker: 
            price_col: Nom de la colonne prix ('Close', 'Open', etc.)
            start_date: Date de début de la requête
            end_date: Date de fin de la requête
        
        Returns:
            tuple: (dataframe, status, gap_range)
            - dataframe: Données en cache ou None
            - status: Type de correspondance
            - gap_range: (gap_start, gap_end) si overlap, sinon None
        """
        if not self.cache_dir.exists():
            return (None, "miss", None)

        # Itération sur les fichiers du cache pour match (ticker, price_col)
        for file_path in self.cache_dir.iterdir():
            if not file_path.is_file() or file_path.suffix != '.pkl':
                continue

            try:
                # Parse le nom du fichier
                name_parts = file_path.stem.split('_')
                
                # Vérification du format attendu
                if len(name_parts) < 4:
                    continue
                
                cached_ticker = name_parts[0]
                cached_col = name_parts[1]
                cached_start_str = name_parts[2]
                cached_end_str = name_parts[3]

                # Vérifier la correspondance ticker + price_col
                if cached_ticker != ticker or cached_col != price_col:
                    continue

                # Parser les dates
                cached_start = pd.to_datetime(cached_start_str)
                cached_end = pd.to_datetime(cached_end_str)

                # Déterminer le type d'overlap
                status, gap_start, gap_end = self._check_date_overlap(
                    cached_start, cached_end, start_date, end_date
                )

                if status != "miss":
                    with open(file_path, 'rb') as f:
                        data = pickle.load(f)

                    # Reconstruire le DataFrame avec les dates
                    prices_list = data['prices']
                    dates_list = data.get('dates') # méthode pandas sur dataframe
                    
                    df = pd.DataFrame({price_col: prices_list})
                    
                    if dates_list is not None:
                        # Utiliser les dates réelles stockées
                        df.index = pd.to_datetime(dates_list)
                    else:
                        # Fallback: utiliser les jours ouvrés
                        date_range = pd.bdate_range(
                            start=cached_start, 
                            periods=len(df)
                        )
                        df.index = date_range

                    if status == "exact":
                        return (df, "exact", None)
                    elif status == "contains":
                        return (df, "contains", None)
                    elif status.startswith("overlap"):
                        return (df, status, (gap_start, gap_end))

            except (ValueError, KeyError, pickle.UnpicklingError) as e:
                # Ignorer les fichiers cache corrompus
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
        """
        Sauvegarde les prix dans un fichier cache avec metadata
        """
        data = {
            "ticker": ticker,
            "start": start,
            "end": end,
            "fetched_at": datetime.now().isoformat(),
            "n_prices": len(prices),
            "prices": prices,
            "dates": dates
        }
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)
        self.logger.debug(f"Cache sauvegardé: {cache_path}")
    
    def fetch_single_ticker(
        self, 
        ticker: str, 
        price_col: str, 
        dates: tuple[str, str]
    ) -> PriceSeries | None:
        
        start_req = pd.to_datetime(dates[0])
        end_req = pd.to_datetime(dates[1])
        
        # 1. Tenter de charger depuis le cache
        df_cached, status, gap = self._load_from_cache(ticker, price_col, start_req, end_req)
        
        df_final = None

        if status == "exact" or status == "contains":
            self.logger.info(f"Cache HIT ({status}) pour {ticker}")
            df_final = df_cached.loc[start_req:end_req]
            
        elif status.startswith("overlap"):
            self.logger.info(f"Cache OVERLAP pour {ticker}. Récupération du gap...")
            gap_start, gap_end = gap
            # Fetch la partie manquante sur Yahoo Finance
            new_data = yf.download(ticker, start=gap_start, end=gap_end, progress=False)
            if not new_data.empty:
                df_gap = new_data[[price_col]]
                df_final = pd.concat([df_cached, df_gap]).sort_index()
                df_final = df_final[~df_final.index.duplicated(keep='first')]
                # Sauvegarder la version étendue
                new_start = df_final.index.min().strftime('%Y-%m-%d')
                new_end = df_final.index.max().strftime('%Y-%m-%d')
                path = self._get_cache_path(ticker, price_col, (new_start, new_end))
                self._save_to_cache(path, df_final[price_col].tolist(), df_final.index.tolist(), ticker, new_start, new_end)
        
        else: # MISS
            self.logger.info(f"Cache MISS pour {ticker}. Téléchargement complet...")
            data = yf.download(ticker, start=dates[0], end=dates[1], progress=False)
            if not data.empty:
                df_final = data[[price_col]]
                path = self._get_cache_path(ticker, price_col, dates)
                self._save_to_cache(path, df_final[price_col].tolist(), df_final.index.tolist(), ticker, dates[0], dates[1])

        if df_final is not None:
            # On retourne l'objet PriceSeries (assure-toi que PriceSeries accepte un dataframe ou une série)
            return PriceSeries(df_final[price_col])
        
        return None
    
    def fetch_multiple_tickers(
        self,
        tickers: Sequence[str],
        price_col: str,
        dates: tuple[str, str]
    ) -> dict[str, PriceSeries]:
        """
        Récupère les données de prix pour plusieurs tickers.
        
        Returns:
            Dictionnaire {ticker: PriceSeries}
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
        # Itérer sur les fichiers d'un directory tout en vérifiant le suffix
            # supprimer
        # Renvoyer le nombre de fichier supprimé
        count = 0
        for file in self.cache_dir.glob("*.pkl"):
            file.unlink()
            count += 1
        self.logger.info(f"Cache nettoyé : {count} fichiers supprimés.")
        return count
