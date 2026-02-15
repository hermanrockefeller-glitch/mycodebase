"""Parse broker shorthand for option structure orders.

Supported formats:
    "BUY 100 AAPL Jan25 150/160 call spread"
    "SELL 50 SPY Mar25 450 put"
    "BUY 10 TSLA Feb25 200 straddle"
    "BUY 20 MSFT Apr25 300/320 put spread"
    "BUY 10 AAPL Jun25 150/160 strangle"
    "BUY 5 AMZN Jul25 180/190/200 call butterfly"
    "BUY 10 GOOGL Sep25 150P/160C risk reversal"
    "BUY 10 META Dec25 400P/450C collar"
"""

import re
from datetime import date

from .models import OptionLeg, OptionStructure, OptionType, Side

# Map 3-letter month abbreviations to month numbers
_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_expiry(expiry_str: str) -> date:
    """Parse expiry like 'Jan25' -> date(2025, 1, 16) (3rd Friday approx)."""
    match = re.match(r"([A-Za-z]{3})(\d{2})", expiry_str)
    if not match:
        raise ValueError(f"Cannot parse expiry: {expiry_str}")
    month_str, year_str = match.groups()
    month = _MONTHS.get(month_str.lower())
    if month is None:
        raise ValueError(f"Unknown month: {month_str}")
    year = 2000 + int(year_str)
    # Approximate standard expiry as 3rd Friday (day 15-21 range, use 16)
    return date(year, month, 16)


def _parse_strikes(strike_str: str) -> list[tuple[float, OptionType | None]]:
    """Parse strikes like '150/160', '150P/160C', or '150'."""
    parts = strike_str.split("/")
    results = []
    for part in parts:
        match = re.match(r"([\d.]+)([PCpc])?", part)
        if not match:
            raise ValueError(f"Cannot parse strike: {part}")
        strike = float(match.group(1))
        type_char = match.group(2)
        if type_char:
            opt_type = OptionType.CALL if type_char.upper() == "C" else OptionType.PUT
        else:
            opt_type = None
        results.append((strike, opt_type))
    return results


def parse_order(text: str) -> OptionStructure:
    """Parse a broker shorthand order string into an OptionStructure.

    Args:
        text: Order string, e.g. "BUY 100 AAPL Jan25 150/160 call spread"

    Returns:
        OptionStructure with parsed legs.

    Raises:
        ValueError: If the order string cannot be parsed.
    """
    tokens = text.strip().split()
    if len(tokens) < 5:
        raise ValueError(f"Order too short: {text}")

    # Parse side and quantity
    side_str = tokens[0].upper()
    if side_str not in ("BUY", "SELL"):
        raise ValueError(f"Expected BUY or SELL, got: {side_str}")
    side = Side.BUY if side_str == "BUY" else Side.SELL
    opposite_side = Side.SELL if side == Side.BUY else Side.BUY

    try:
        quantity = int(tokens[1])
    except ValueError:
        raise ValueError(f"Expected quantity, got: {tokens[1]}")

    underlying = tokens[2].upper()
    expiry = _parse_expiry(tokens[3])

    # Parse strikes
    strikes = _parse_strikes(tokens[4])

    # Remaining tokens determine structure type and option type
    remaining = [t.lower() for t in tokens[5:]]

    # Detect structure type
    structure_type = _detect_structure(remaining, strikes)

    # Detect option type from remaining tokens (if not embedded in strikes)
    default_type = _detect_option_type(remaining)

    # Build legs based on structure type
    legs = _build_legs(
        structure_type, underlying, expiry, strikes, default_type,
        side, opposite_side, quantity,
    )

    description = f"{side_str} {quantity}x {underlying} {tokens[3]} {structure_type}"
    return OptionStructure(name=structure_type, legs=legs, description=description)


def _detect_structure(remaining: list[str], strikes: list) -> str:
    """Detect the structure type from remaining tokens and strike count."""
    for token in remaining:
        if token in ("spread", "straddle", "strangle", "butterfly", "collar"):
            return token
        if token == "risk" and "reversal" in remaining:
            return "risk reversal"
    # Default: if single strike, it's a single option
    if len(strikes) == 1:
        return "single"
    if len(strikes) == 2:
        return "spread"
    if len(strikes) == 3:
        return "butterfly"
    return "custom"


def _detect_option_type(remaining: list[str]) -> OptionType | None:
    """Detect call/put from remaining tokens."""
    for token in remaining:
        if token == "call":
            return OptionType.CALL
        if token == "put":
            return OptionType.PUT
    return None


def _build_legs(
    structure_type: str,
    underlying: str,
    expiry: date,
    strikes: list[tuple[float, OptionType | None]],
    default_type: OptionType | None,
    side: Side,
    opposite_side: Side,
    quantity: int,
) -> list[OptionLeg]:
    """Build option legs based on the structure type."""

    def _resolve_type(
        strike_type: OptionType | None, fallback: OptionType | None
    ) -> OptionType:
        t = strike_type or fallback
        if t is None:
            raise ValueError("Cannot determine option type (call or put)")
        return t

    if structure_type == "single":
        strike, strike_type = strikes[0]
        return [
            OptionLeg(
                underlying=underlying, expiry=expiry, strike=strike,
                option_type=_resolve_type(strike_type, default_type),
                side=side, quantity=quantity,
            )
        ]

    if structure_type == "spread":
        if len(strikes) != 2:
            raise ValueError("Spread requires exactly 2 strikes")
        s1, t1 = strikes[0]
        s2, t2 = strikes[1]
        opt_type = _resolve_type(t1, default_type)
        return [
            OptionLeg(
                underlying=underlying, expiry=expiry, strike=s1,
                option_type=_resolve_type(t1, default_type),
                side=side, quantity=quantity,
            ),
            OptionLeg(
                underlying=underlying, expiry=expiry, strike=s2,
                option_type=_resolve_type(t2, default_type),
                side=opposite_side, quantity=quantity,
            ),
        ]

    if structure_type == "straddle":
        if len(strikes) != 1:
            raise ValueError("Straddle requires exactly 1 strike")
        strike = strikes[0][0]
        return [
            OptionLeg(
                underlying=underlying, expiry=expiry, strike=strike,
                option_type=OptionType.CALL, side=side, quantity=quantity,
            ),
            OptionLeg(
                underlying=underlying, expiry=expiry, strike=strike,
                option_type=OptionType.PUT, side=side, quantity=quantity,
            ),
        ]

    if structure_type == "strangle":
        if len(strikes) != 2:
            raise ValueError("Strangle requires exactly 2 strikes")
        s_low, s_high = sorted(s for s, _ in strikes)
        return [
            OptionLeg(
                underlying=underlying, expiry=expiry, strike=s_low,
                option_type=OptionType.PUT, side=side, quantity=quantity,
            ),
            OptionLeg(
                underlying=underlying, expiry=expiry, strike=s_high,
                option_type=OptionType.CALL, side=side, quantity=quantity,
            ),
        ]

    if structure_type == "butterfly":
        if len(strikes) != 3:
            raise ValueError("Butterfly requires exactly 3 strikes")
        sorted_strikes = sorted(s for s, _ in strikes)
        opt_type = _resolve_type(strikes[0][1], default_type)
        return [
            OptionLeg(
                underlying=underlying, expiry=expiry, strike=sorted_strikes[0],
                option_type=opt_type, side=side, quantity=quantity,
            ),
            OptionLeg(
                underlying=underlying, expiry=expiry, strike=sorted_strikes[1],
                option_type=opt_type, side=opposite_side, quantity=quantity * 2,
            ),
            OptionLeg(
                underlying=underlying, expiry=expiry, strike=sorted_strikes[2],
                option_type=opt_type, side=side, quantity=quantity,
            ),
        ]

    if structure_type in ("risk reversal", "collar"):
        if len(strikes) != 2:
            raise ValueError(f"{structure_type} requires exactly 2 strikes")
        s1, t1 = strikes[0]
        s2, t2 = strikes[1]
        # Resolve types: first strike is put, second is call (typical convention)
        type1 = t1 or OptionType.PUT
        type2 = t2 or OptionType.CALL
        if structure_type == "risk reversal":
            return [
                OptionLeg(
                    underlying=underlying, expiry=expiry, strike=s1,
                    option_type=type1, side=opposite_side, quantity=quantity,
                ),
                OptionLeg(
                    underlying=underlying, expiry=expiry, strike=s2,
                    option_type=type2, side=side, quantity=quantity,
                ),
            ]
        else:  # collar
            return [
                OptionLeg(
                    underlying=underlying, expiry=expiry, strike=s1,
                    option_type=type1, side=side, quantity=quantity,
                ),
                OptionLeg(
                    underlying=underlying, expiry=expiry, strike=s2,
                    option_type=type2, side=opposite_side, quantity=quantity,
                ),
            ]

    raise ValueError(f"Unknown structure type: {structure_type}")
