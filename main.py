import matplotlib.pyplot as plt
from Bridge789 import validate_and_fix_prices


def prices_graph(prices: dict[str, float]) -> None:
    plt.figure()
    deductibles = [100, 200, 500]

    limited_casco = [prices[f"limited_casco_{d}"] for d in deductibles]
    casco = [prices[f"casco_{d}"] for d in deductibles]
    mtpl = [prices["mtpl"]] * len(deductibles)

    # Plot each product line
    plt.plot(
        deductibles,
        mtpl,
        label="MTPL (Baseline)",
        marker="s",
        linestyle="--",
        color="gray",
    )
    plt.plot(
        deductibles, limited_casco, label="Limited Casco", marker="o", color="orange"
    )
    plt.plot(deductibles, casco, label="Casco", marker="o", color="blue")

    plt.xlabel("Deductible (€)", fontsize=12)
    plt.ylabel("Premium Price (€)", fontsize=12)
    plt.xticks(deductibles)
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.legend(fontsize=11)

    plt.tight_layout()


def prices_diff_graph(
    original: dict[str, float], fixed: dict[str, float], title=None
) -> None:
    plt.figure(figsize=(10, 6))
    deductibles = [100, 200, 500]

    # helper to extract values for plotting
    def get_coords(d_map, product):
        if product == "mtpl":
            return [d_map["mtpl"]] * len(deductibles)
        return [d_map[f"{product}_{d}"] for d in deductibles]

    products = [
        ("mtpl", "MTPL", "gray"),
        ("limited_casco", "Limited Casco", "orange"),
        ("casco", "Casco", "blue"),
    ]

    for key, label, color in products:
        old_vals = get_coords(original, key)
        new_vals = get_coords(fixed, key)

        # Plot original prices (dashed, transparent)
        plt.plot(
            deductibles,
            old_vals,
            linestyle="--",
            marker="x",
            color=color,
            alpha=0.3,
            label=f"{label} (Original)",
        )

        # Plot fixed prices (solid)
        plt.plot(
            deductibles,
            new_vals,
            linestyle="-",
            marker="o",
            color=color,
            linewidth=2,
            label=f"{label} (Fixed)",
        )

    if not title is None:
        plt.title(title)

    plt.xlabel("Deductible (€)", fontsize=12)
    plt.ylabel("Premium Price (€)", fontsize=12)
    plt.xticks(deductibles)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plt.show()


def run_unit_tests(test_cases: dict[str, dict], details=True, show_graphs=False):
    print("--- RUNNING EDGE CASE TESTS ---\n")
    for ind, (test_name, test_data) in enumerate(test_cases.items()):
        prices = test_data["prices"]
        expected_issues = test_data["expected_issues"]

        print(f"=== {ind + 1}. {test_name} ===")
        result = validate_and_fix_prices(prices)
        issues_returned = result["issues"]
        actual_issues = len(issues_returned)

        if details:
            print(f"Input:  {prices}")
            print(f"Output: {result['fixed_prices']}")
            print(
                f"Expected Issues: {expected_issues} | Actual Issues: {actual_issues}"
            )
            print("Issues Fixed:")
            if not issues_returned:
                print("  - None (Perfect!)")
            else:
                for issue in issues_returned:
                    print(f"  - {issue}")

        # Validation checks
        fp = result["fixed_prices"]
        is_prices_valid = (
            fp["mtpl"] < fp["limited_casco_500"]
            and fp["limited_casco_500"]
            < fp["limited_casco_200"]
            < fp["limited_casco_100"]
            and fp["casco_500"] < fp["casco_200"] < fp["casco_100"]
            and all(
                fp[f"casco_{d}"] > fp[f"limited_casco_{d}"]
                for d in ["100", "200", "500"]
            )
        )
        is_step_count_valid = actual_issues == expected_issues

        if is_prices_valid and is_step_count_valid:
            print("Verdict: ✅ PASSED\n")
        else:
            print("Verdict: ❌ FAILED")
            if not is_prices_valid:
                print("  -> Reason: Math/hierarchy validation failed.")
            if not is_step_count_valid:
                print(
                    f"  -> Reason: Step count mismatch (Expected {expected_issues}, Got {actual_issues})."
                )
            print("\n")

        if show_graphs:
            prices_diff_graph(prices, fp, title=f"{ind + 1}. {test_name}")


if __name__ == "__main__":
    test_cases = {
        "Problem Example": {
            "prices": {
                "mtpl": 400,
                "limited_casco_100": 850,
                "limited_casco_200": 900,
                "limited_casco_500": 700,
                "casco_100": 780,
                "casco_200": 950,
                "casco_500": 830,
            },
            "expected_issues": 2,
        },
        "The Original Edge Case (Squeeze Logic)": {
            "prices": {
                "mtpl": 1000,
                "limited_casco_100": 950,
                "limited_casco_200": 900,
                "limited_casco_500": 500,
                "casco_100": 1000,
                "casco_200": 800,  # Fails hierarchy
                "casco_500": 600,
            },
            "expected_issues": 2,
        },
        "Perfect Input (Should touch nothing)": {
            "prices": {
                "mtpl": 400,
                "limited_casco_100": 850,
                "limited_casco_200": 720,
                "limited_casco_500": 680,
                "casco_100": 1200,
                "casco_200": 1020,
                "casco_500": 960,
            },
            "expected_issues": 0,
        },
        "Completely Inverted Hierarchy": {
            "prices": {
                "mtpl": 1500,  # MTPL is the most expensive
                "limited_casco_100": 1000,
                "limited_casco_200": 900,
                "limited_casco_500": 800,
                "casco_100": 500,  # Casco is the cheapest
                "casco_200": 400,
                "casco_500": 300,
            },
            "expected_issues": 4,
        },
        "Completely Inverted Deductibles": {
            "prices": {
                "mtpl": 300,
                "limited_casco_100": 700,
                "limited_casco_200": 800,  # Higher deductible costs more
                "limited_casco_500": 900,  # Highest deductible costs most
                "casco_100": 1000,
                "casco_200": 1100,
                "casco_500": 1200,
            },
            "expected_issues": 4,
        },
        "Flat Pricing (Equal values)": {
            "prices": {
                "mtpl": 800,
                "limited_casco_100": 800,
                "limited_casco_200": 800,
                "limited_casco_500": 800,
                "casco_100": 800,
                "casco_200": 800,
                "casco_500": 800,
            },
            "expected_issues": 6,
        },
        "Severe Multi-Price Corruption (Chaos)": {
            "prices": {
                "mtpl": 9999,
                "limited_casco_100": 10,
                "limited_casco_200": 5000,
                "limited_casco_500": 20,
                "casco_100": 15,
                "casco_200": 6000,
                "casco_500": 5,
            },
            "expected_issues": 5,
        },
        "Very Low Initial values (Chaos)": {
            "prices": {
                "mtpl": 5,
                "limited_casco_100": 3,
                "limited_casco_200": 2,
                "limited_casco_500": 1,
                "casco_100": 1,
                "casco_200": 2,
                "casco_500": 1,
            },
            "expected_issues": 4,
        },
        "Sub-optimal 100€ Fix (Anchor to 500)": {
            "prices": {
                "mtpl": 400,
                "limited_casco_100": 850,
                "limited_casco_200": 860,
                "limited_casco_500": 800,
                "casco_100": 1500,
                "casco_200": 1200,
                "casco_500": 1000,
            },
            "expected_issues": 1,
        },
    }

    run_unit_tests(test_cases, details=False, show_graphs=True)
