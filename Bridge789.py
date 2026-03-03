def validate_and_fix_prices(prices: dict[str, float]) -> dict:
    """
    Validates and automatically corrects insurance pricing to ensure compliance
    with defined product hierarchies and deductible risk-pricing rules.

    The algorithm treats the input dictionary as the ground truth. If a given set
    of prices naturally obeys all strict ordering rules, it remains untouched, even
    if the deductible margins deviate from the baseline 15%/20% heuristic.
    Adjustments are strictly reserved for resolving absolute logical violations,
    ensuring that valid market variances are preserved and customer impact is minimized.

    Validation Rules Enforced:
    1. Deductible Risk Principle: Higher deductibles represent higher customer risk,
       requiring lower premiums: price(500€) < price(200€) < price(100€).
    2. Coverage Hierarchy Principle: MTPL < Limited Casco < Casco.

    Algorithmic Strategy:
    - When a violation is detected, the 15% (for 200€) and
      20% (for 500€) guidelines are utilized alongside derived market average ratios
      to calculate mathematically sound baselines.
    - The algorithm generates multiple single-price adjustment candidates
      and applies the one that yields the smallest absolute difference from the original
      ground truth.
    - Enforces cross-product hierarchy bounds to prevent an adjustment
      in one product tier from triggering a cascading violation in another.

    Args:
        prices (dict[str, float]): The initial dictionary of insurance prices.
            Keys follow the format 'mtpl', 'limited_casco_{deductible}', etc.

    Returns:
        dict: A formatted dictionary containing:
            - "fixed_prices" (dict[str, float]): The full corrected price dictionary.
            - "issues" (list[str]): Plain English explanations for each applied fix.
    """
    # Define proportional adjustments based on the deductible guide.
    RATIO_200_DEDUCTIBLE = 0.85  # Represents roughly -15% relative to 100 EUR base.
    RATIO_500_DEDUCTIBLE = 0.80  # Represents roughly -20% relative to 100 EUR base.

    # Ratios derived from average market prices to ensure proportional adjustments.
    RATIO_MTPL_TO_LC = 500 / 900
    RATIO_CASCO_TO_LC = 1200 / 900

    initial_prices = prices.copy()
    fixed_prices = prices.copy()

    def round_price(val: float) -> float:
        return round(float(val), 2)

    def is_valid_sequence(price_100: float, price_200: float, price_500: float) -> bool:
        return price_500 < price_200 < price_100

    def optimize_deductibles(product_prefix: str, lower_bounds: dict = None):
        price_100 = fixed_prices[f"{product_prefix}_100"]
        price_200 = fixed_prices[f"{product_prefix}_200"]
        price_500 = fixed_prices[f"{product_prefix}_500"]

        if is_valid_sequence(price_100, price_200, price_500):
            return

        candidates = []
        lower_bounds = lower_bounds or {}

        # Keep fixes minimal by testing single-price adjustments first.

        # Scenario A1: Fix 100 EUR deductible based on the 200 EUR price
        new_100_from_200 = round_price(price_200 / RATIO_200_DEDUCTIBLE)
        if is_valid_sequence(
            new_100_from_200, price_200, price_500
        ) and new_100_from_200 > lower_bounds.get("100", 0):
            candidates.append(
                (
                    abs(new_100_from_200 - price_100),
                    new_100_from_200,
                    price_200,
                    price_500,
                )
            )

        # Scenario A2: Fix 100 EUR deductible based on the 500 EUR price
        new_100_from_500 = round_price(price_500 / RATIO_500_DEDUCTIBLE)
        if is_valid_sequence(
            new_100_from_500, price_200, price_500
        ) and new_100_from_500 > lower_bounds.get("100", 0):
            candidates.append(
                (
                    abs(new_100_from_500 - price_100),
                    new_100_from_500,
                    price_200,
                    price_500,
                )
            )

        # Scenario B: Fix only the 200 EUR deductible
        new_200 = round_price(price_100 * RATIO_200_DEDUCTIBLE)
        if is_valid_sequence(
            price_100, new_200, price_500
        ) and new_200 > lower_bounds.get("200", 0):
            candidates.append((abs(new_200 - price_200), price_100, new_200, price_500))

        # Scenario C: Fix only the 500 EUR deductible
        new_500 = round_price(price_100 * RATIO_500_DEDUCTIBLE)
        if is_valid_sequence(
            price_100, price_200, new_500
        ) and new_500 > lower_bounds.get("500", 0):
            candidates.append((abs(new_500 - price_500), price_100, price_200, new_500))

        # Apply the fix with the absolute minimum disruption
        if candidates:
            candidates.sort(key=lambda x: x[0])
            _, best_100, best_200, best_500 = candidates[0]

            fixed_prices[f"{product_prefix}_100"] = best_100
            fixed_prices[f"{product_prefix}_200"] = best_200
            fixed_prices[f"{product_prefix}_500"] = best_500
        else:
            # Failsafe logic to establish a new valid baseline if the tier is heavily corrupted
            base_100 = price_100
            if base_100 <= lower_bounds.get("100", 0):
                base_100 = lower_bounds.get("100", 0) + 50

            new_200 = round_price(base_100 * RATIO_200_DEDUCTIBLE)
            new_500 = round_price(base_100 * RATIO_500_DEDUCTIBLE)

            if new_200 <= lower_bounds.get("200", 0):
                new_200 = lower_bounds.get("200", 0) + 10
            if new_500 <= lower_bounds.get("500", 0):
                new_500 = lower_bounds.get("500", 0) + 10

            fixed_prices[f"{product_prefix}_100"] = base_100
            fixed_prices[f"{product_prefix}_200"] = new_200
            fixed_prices[f"{product_prefix}_500"] = new_500

    # Optimize internal deductibles to ensure the deductible ordering rule is respected.
    optimize_deductibles("limited_casco")
    optimize_deductibles("casco")

    # Enforce product hierarchy: MTPL < Limited Casco < Casco.

    # Check the relationship between MTPL and the cheapest Limited Casco product
    if fixed_prices["mtpl"] >= fixed_prices["limited_casco_500"]:
        adjusted_mtpl = round_price(
            fixed_prices["limited_casco_100"] * RATIO_MTPL_TO_LC
        )

        # Failsafe if we can't set MTPL based on LC100, we set it as 90% of LC500
        if adjusted_mtpl >= fixed_prices["limited_casco_500"]:
            adjusted_mtpl = round_price(fixed_prices["limited_casco_500"] * 0.90)

        fixed_prices["mtpl"] = adjusted_mtpl

    # Check the relationship between Casco and Limited Casco for matching deductibles
    for deductible in ["100", "200", "500"]:
        lc_price = fixed_prices[f"limited_casco_{deductible}"]
        casco_price = fixed_prices[f"casco_{deductible}"]

        if casco_price <= lc_price:
            new_casco_price = round_price(lc_price * RATIO_CASCO_TO_LC)

            # Squeeze logic to ensure adjusting a lower deductible doesn't overtake a higher one
            upper_bound = None
            if deductible == "200":
                upper_bound = fixed_prices["casco_100"]
            if deductible == "500":
                upper_bound = fixed_prices["casco_200"]

            if upper_bound and new_casco_price >= upper_bound:
                if lc_price < upper_bound:
                    new_casco_price = round_price((lc_price + upper_bound) / 2)
                else:
                    new_casco_price = round_price(lc_price * 1.05)

            fixed_prices[f"casco_{deductible}"] = new_casco_price

    # Hierarchy failsafe to verify internal Casco ordering after hierarchy adjustments
    if not is_valid_sequence(
        fixed_prices["casco_100"], fixed_prices["casco_200"], fixed_prices["casco_500"]
    ):
        casco_lower_bounds = {
            "100": fixed_prices["limited_casco_100"],
            "200": fixed_prices["limited_casco_200"],
            "500": fixed_prices["limited_casco_500"],
        }
        optimize_deductibles("casco", lower_bounds=casco_lower_bounds)

    # Generate logs for automatically fixed violations in plain language.
    issues = []

    for key, initial_val in initial_prices.items():
        final_val = fixed_prices[key]

        # Only report if a net change actually occurred
        if initial_val == final_val:
            continue

        reasons = []

        # Reverse engineer the reason by analyzing the flawed initial state
        if key == "mtpl" and initial_val >= initial_prices["limited_casco_500"]:
            reasons.append("MTPL must be cheaper than Limited Casco")

        if "casco" in key and "limited" not in key:
            deductible_tier = key.split("_")[1]
            if initial_val <= initial_prices[f"limited_casco_{deductible_tier}"]:
                reasons.append(
                    f"Casco must be more expensive than Limited Casco at the {deductible_tier}€ deductible"
                )

        if key != "mtpl":
            prefix = "limited_casco" if "limited" in key else "casco"
            orig_100 = initial_prices[f"{prefix}_100"]
            orig_200 = initial_prices[f"{prefix}_200"]
            orig_500 = initial_prices[f"{prefix}_500"]

            if not is_valid_sequence(orig_100, orig_200, orig_500):
                reasons.append(
                    "the internal deductible ordering was invalid (higher deductibles must cost less)"
                )

        reason_string = (
            " and ".join(reasons)
            if reasons
            else "to resolve overlapping pricing violations caused by adjusting other products"
        )
        issues.append(
            f"Adjusted '{key}' from {initial_val} to {final_val} because {reason_string}."
        )

    # Return exactly the expected dictionary format.
    return {"fixed_prices": fixed_prices, "issues": issues}
