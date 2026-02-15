"""Data models for option legs and structures."""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class OptionType(Enum):
    CALL = "call"
    PUT = "put"


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class OptionLeg:
    """A single option leg within a structure."""

    underlying: str
    expiry: date
    strike: float
    option_type: OptionType
    side: Side
    quantity: int = 1

    @property
    def direction(self) -> int:
        """Return +1 for buy, -1 for sell."""
        return 1 if self.side == Side.BUY else -1

    def payoff(self, spot: float) -> float:
        """Calculate per-unit payoff at expiration for a given spot price."""
        if self.option_type == OptionType.CALL:
            intrinsic = max(spot - self.strike, 0.0)
        else:
            intrinsic = max(self.strike - spot, 0.0)
        return self.direction * self.quantity * intrinsic


@dataclass
class OptionStructure:
    """A multi-leg option structure (spread, straddle, etc.)."""

    name: str
    legs: list[OptionLeg] = field(default_factory=list)
    description: str = ""

    def total_payoff(self, spot: float) -> float:
        """Calculate total structure payoff at a given spot price."""
        return sum(leg.payoff(spot) for leg in self.legs)

    def payoff_range(
        self, spot_low: float, spot_high: float, steps: int = 200
    ) -> list[tuple[float, float]]:
        """Calculate payoff across a range of spot prices."""
        step_size = (spot_high - spot_low) / steps
        return [
            (spot_low + i * step_size, self.total_payoff(spot_low + i * step_size))
            for i in range(steps + 1)
        ]

    @property
    def net_quantity(self) -> int:
        return sum(leg.direction * leg.quantity for leg in self.legs)

    @property
    def underlyings(self) -> set[str]:
        return {leg.underlying for leg in self.legs}
