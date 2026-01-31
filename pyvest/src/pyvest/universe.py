from asset import Asset
from typing import Iterator


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