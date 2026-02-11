"""Abstract base class for external data providers."""

from abc import ABC, abstractmethod
from typing import Any


class BaseDataProvider(ABC):
    """Interface for external data sources (SEMrush, Crunchbase, G2, etc.).

    Implementations can be real API clients or mock providers.
    Agents code against this interface and never know the difference.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    def is_available(self) -> bool:
        """Override to check API key availability."""
        return True

    @abstractmethod
    async def get_data(self, company_url: str, **kwargs) -> dict[str, Any]:
        """Fetch data for a company. Returns structured dict."""
        ...
