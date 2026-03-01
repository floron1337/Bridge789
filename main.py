# FIRSTNAME_LASTNAME.py


def validate_and_fix_prices(prices: dict[str, float]) -> dict:
    """
    Validates and fixes motor insurance pricing rules correctly.

    Ensures that product hierarchies (mtpl < Limited Casco < Casco) and
    deductible hierarchies (500 < 200 < 100) are mathematically respected.
    If violations are encountered, corrections are applied minimally and
    proportionally according to the deductible baseline guide (-15% for
    the 200€ tier, -20% for the 500€ tier).

    Args:
        prices: dict with keys like "mtpl", "limited_casco_100", "casco_500"

    Returns:
        {
            "fixed_prices": dict[str, float],
            "issues": list[str]
        }
    """
    fixed = {}
    for k, v in prices.items():
        # Transparently handle baseline alias required by internal logic constraints
        key = "mtpl" if k == "mtpl" else k
        fixed[key] = float(v)

    issues = set()

    def log_issue(msg: str) -> None:
        issues.add(msg)

    def enforce_deductibles(
        prefix: str, product_name: str, min_bounds: dict[str, float] = None
    ) -> None:
        """
        Calculates minimal deviations required to correct inconsistencies
        in deducible sequences, optionally bounded by lower limits.
        """
        p100 = fixed[f"{prefix}_100"]
        p200 = fixed[f"{prefix}_200"]
        p500 = fixed[f"{prefix}_500"]

        valid_internal = p500 < p200 < p100
        valid_bounds = True

        if min_bounds:
            valid_bounds = (
                p100 > min_bounds["100"]
                and p200 > min_bounds["200"]
                and p500 > min_bounds["500"]
            )

        if valid_internal and valid_bounds:
            return

        candidates = []

        def evaluate(c100: float, c200: float, c500: float, reason: str) -> None:
            """Evaluates a proportionally scaled candidate block."""
            if c500 < c200 < c100:
                if min_bounds and not (
                    c100 > min_bounds["100"]
                    and c200 > min_bounds["200"]
                    and c500 > min_bounds["500"]
                ):
                    return
                # L1 norm cost measures deviation magnitude to keep fixes minimal
                diff = abs(c100 - p100) + abs(c200 - p200) + abs(c500 - p500)
                candidates.append((diff, c100, c200, c500, reason))

        # Test proportional scenarios by individually trusting each deductible as the ground-truth base
        evaluate(
            p100,
            round(p100 * 0.85, 2),
            round(p100 * 0.80, 2),
            f"Adjusted {product_name} prices proportionally based on the 100€ baseline to satisfy pricing rules.",
        )

        b100_200 = p200 / 0.85
        evaluate(
            round(b100_200, 2),
            p200,
            round(b100_200 * 0.80, 2),
            f"Adjusted {product_name} prices proportionally based on the 200€ baseline to satisfy pricing rules.",
        )

        b100_500 = p500 / 0.80
        evaluate(
            round(b100_500, 2),
            round(b100_500 * 0.85, 2),
            p500,
            f"Adjusted {product_name} prices proportionally based on the 500€ baseline to satisfy pricing rules.",
        )

        if candidates:
            # Elect candidate with the lowest deviation, resolving violations optimally
            candidates.sort(key=lambda x: x[0])
            _, best100, best200, best500, reason = candidates[0]

            fixed[f"{prefix}_100"] = best100
            fixed[f"{prefix}_200"] = best200
            fixed[f"{prefix}_500"] = best500
            log_issue(reason)
        else:
            # Failsafe: Regimes requiring intense correction typically need structural regeneration above safe bounds
            safe_base = max(
                p100,
                min_bounds["100"] * 1.05 if min_bounds else 0,
                (min_bounds["200"] * 1.05) / 0.85 if min_bounds else 0,
                (min_bounds["500"] * 1.05) / 0.80 if min_bounds else 0,
            )
            safe_base = round(safe_base, 2)

            fixed[f"{prefix}_100"] = safe_base
            fixed[f"{prefix}_200"] = round(safe_base * 0.85, 2)
            fixed[f"{prefix}_500"] = round(safe_base * 0.80, 2)
            log_issue(
                f"Regenerated {product_name} prices upwards structurally to guarantee correct mathematical hierarchy."
            )

    # 1. Enforce Limited Casco deductible dependencies
    enforce_deductibles("limited_casco", "Limited Casco")

    # 2. Enforce Casco > Limited Casco constraint
    casco_bounds = {
        "100": fixed["limited_casco_100"],
        "200": fixed["limited_casco_200"],
        "500": fixed["limited_casco_500"],
    }
    enforce_deductibles("casco", "Casco", min_bounds=casco_bounds)

    # 3. Enforce mtpl < Limited Casco constraint
    if fixed["mtpl"] >= fixed["limited_casco_500"]:
        fixed["mtpl"] = round(fixed["limited_casco_500"] * 0.90, 2)
        log_issue(
            "Reduced mtpl price gracefully to ensure it remains cheaper than Limited Casco."
        )

    return {"fixed_prices": fixed, "issues": sorted(list(issues))}


import random


def generate_random_test_case() -> dict[str, float]:
    """Generates a random dictionary of prices to stress test the logic."""
    base = random.uniform(100, 2000)

    # 50% chance for "somewhat structured but wrong", 50% chance for "pure chaos"
    if random.random() > 0.5:
        prices = {
            "mtpl": base * random.uniform(0.5, 1.2),
            "limited_casco_100": base * random.uniform(1.1, 2.5),
            "limited_casco_200": base * random.uniform(0.9, 2.2),
            "limited_casco_500": base * random.uniform(0.7, 2.0),
            "casco_100": base * random.uniform(1.5, 3.5),
            "casco_200": base * random.uniform(1.3, 3.0),
            "casco_500": base * random.uniform(1.0, 2.5),
        }
    else:
        prices = {
            "mtpl": random.uniform(10, 5000),
            "limited_casco_100": random.uniform(10, 5000),
            "limited_casco_200": random.uniform(10, 5000),
            "limited_casco_500": random.uniform(10, 5000),
            "casco_100": random.uniform(10, 5000),
            "casco_200": random.uniform(10, 5000),
            "casco_500": random.uniform(10, 5000),
        }

    return {k: round(v, 2) for k, v in prices.items()}


def run_stress_test(iterations: int = 1000):
    print(f"\n--- RUNNING STRESS TEST ({iterations} iterations) ---")
    passed = 0
    failed = 0

    for i in range(iterations):
        initial_prices = generate_random_test_case()

        try:
            result = validate_and_fix_prices(initial_prices)
            fp = result["fixed_prices"]

            # Check all mathematical invariants
            is_valid = (
                fp["mtpl"] < fp["limited_casco_500"]
                and fp["limited_casco_500"]
                < fp["limited_casco_200"]
                < fp["limited_casco_100"]
                and fp["casco_500"] < fp["casco_200"] < fp["casco_100"]
                and fp["limited_casco_100"] < fp["casco_100"]
                and fp["limited_casco_200"] < fp["casco_200"]
                and fp["limited_casco_500"] < fp["casco_500"]
            )

            if is_valid:
                passed += 1
            else:
                failed += 1
                print(f"❌ FAILED INVARIANT on iteration {i}:")
                print(f"Original: {initial_prices}")
                print(f"Fixed:    {fp}\n")

        except Exception as e:
            failed += 1
            print(f"🚨 EXCEPTION on iteration {i}: {e}")
            print(f"Original: {initial_prices}\n")

    print(f"Stress Test Completed: {passed} Passed | {failed} Failed")
    print("--------------------------------------------------\n")


# --- Local testing only ---
if __name__ == "__main__":
    example_prices = {
        "mtpl": 400,
        "limited_casco_100": 850,
        "limited_casco_200": 900,
        "limited_casco_500": 700,
        "casco_100": 780,
        "casco_200": 950,
        "casco_500": 830,
    }

    result = validate_and_fix_prices(example_prices)
    print("Fixed prices (Example):")
    for key, value in result["fixed_prices"].items():
        print(f"  {key}: {value}")

    print("\nIssues found (Example):")
    for issue in result["issues"]:
        print(f"  - {issue}")

    run_stress_test(100000)
