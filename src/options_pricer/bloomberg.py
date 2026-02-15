"""Bloomberg API wrapper for live market data.

Provides a mock-friendly interface so the dashboard and tests can run
without a Bloomberg Terminal connection.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class MarketData:
    """Snapshot of market data for an underlying."""

    underlying: str
    spot: float
    implied_vols: dict[tuple[date, float], float] = field(default_factory=dict)
    risk_free_rate: float = 0.05
    dividend_yield: float = 0.0


class BloombergClient:
    """Wrapper around blpapi for fetching live market data.

    When Bloomberg is unavailable, falls back to MockBloombergClient.
    """

    def __init__(self, host: str = "localhost", port: int = 8194):
        self._host = host
        self._port = port
        self._session = None

    def connect(self) -> bool:
        """Attempt to connect to the Bloomberg session."""
        try:
            import blpapi

            session_options = blpapi.SessionOptions()
            session_options.setServerHost(self._host)
            session_options.setServerPort(self._port)
            self._session = blpapi.Session(session_options)
            return self._session.start()
        except (ImportError, Exception):
            return False

    def disconnect(self):
        """Disconnect from Bloomberg."""
        if self._session:
            self._session.stop()
            self._session = None

    def get_spot(self, underlying: str) -> float | None:
        """Fetch the current spot price for an underlying."""
        if not self._session:
            return None
        try:
            import blpapi

            refdata = self._session.getService("//blp/refdata")
            request = refdata.createRequest("ReferenceDataRequest")
            request.append("securities", f"{underlying} US Equity")
            request.append("fields", "PX_LAST")
            self._session.sendRequest(request)

            while True:
                event = self._session.nextEvent(500)
                for msg in event:
                    if msg.hasElement("securityData"):
                        sec_data = msg.getElement("securityData").getValueAsElement(0)
                        field_data = sec_data.getElement("fieldData")
                        return field_data.getElementAsFloat("PX_LAST")
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
        except Exception:
            return None

    def get_implied_vol(
        self, underlying: str, expiry: date, strike: float
    ) -> float | None:
        """Fetch implied volatility for a specific option."""
        if not self._session:
            return None
        # In production, this would construct the option ticker and query Bloomberg
        # e.g., "AAPL 01/16/25 C150 Equity" for AAPL Jan25 150 Call
        return None

    def get_risk_free_rate(self) -> float:
        """Fetch current risk-free rate (US Treasury yield)."""
        if not self._session:
            return 0.05
        # Would query "USGG3M Index" or similar
        return 0.05

    def get_market_data(self, underlying: str) -> MarketData:
        """Fetch a full market data snapshot for an underlying."""
        spot = self.get_spot(underlying)
        rate = self.get_risk_free_rate()
        return MarketData(
            underlying=underlying,
            spot=spot or 0.0,
            risk_free_rate=rate,
        )


class MockBloombergClient:
    """Mock Bloomberg client with sample data for testing and demo purposes."""

    _MOCK_SPOTS: dict[str, float] = {
        "AAPL": 185.50,
        "MSFT": 415.20,
        "GOOGL": 175.80,
        "AMZN": 195.60,
        "TSLA": 245.30,
        "SPY": 520.40,
        "QQQ": 445.10,
        "META": 560.75,
        "NVDA": 880.50,
        "IWM": 205.60,
    }

    _MOCK_VOLS: dict[str, float] = {
        "AAPL": 0.22,
        "MSFT": 0.20,
        "GOOGL": 0.25,
        "AMZN": 0.28,
        "TSLA": 0.45,
        "SPY": 0.14,
        "QQQ": 0.18,
        "META": 0.32,
        "NVDA": 0.42,
        "IWM": 0.18,
    }

    def connect(self) -> bool:
        return True

    def disconnect(self):
        pass

    def get_spot(self, underlying: str) -> float:
        return self._MOCK_SPOTS.get(underlying.upper(), 100.0)

    def get_implied_vol(
        self, underlying: str, expiry: date, strike: float
    ) -> float:
        base_vol = self._MOCK_VOLS.get(underlying.upper(), 0.25)
        # Simple vol skew: OTM puts have higher vol
        spot = self.get_spot(underlying)
        moneyness = strike / spot
        skew = 0.05 * (1.0 - moneyness) if moneyness < 1.0 else 0.0
        return base_vol + skew

    def get_risk_free_rate(self) -> float:
        return 0.05

    def get_market_data(self, underlying: str) -> MarketData:
        return MarketData(
            underlying=underlying,
            spot=self.get_spot(underlying),
            risk_free_rate=self.get_risk_free_rate(),
        )


def create_client(use_mock: bool = False, **kwargs) -> BloombergClient | MockBloombergClient:
    """Factory to create a Bloomberg client, falling back to mock if needed."""
    if use_mock:
        return MockBloombergClient()
    client = BloombergClient(**kwargs)
    if client.connect():
        return client
    # Fall back to mock if Bloomberg is unavailable
    return MockBloombergClient()
