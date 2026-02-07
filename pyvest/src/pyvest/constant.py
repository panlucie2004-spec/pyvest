# Fichier: pyvest/src/constant.py
from enum import StrEnum

class CurrencyEnum(StrEnum):
    """Énumération des devises supportées."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
