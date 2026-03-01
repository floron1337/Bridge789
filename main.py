import matplotlib.pyplot as plt


def prices_graph(prices: dict[str, float]) -> None:
    plt.figure()
    deductibles = [100, 200, 500]

    limited_casco = [prices[f"limited_casco_{d}"] for d in deductibles]
    casco = [prices[f"casco_{d}"] for d in deductibles]
    mtpl = [prices["mtpl"]] * len(deductibles) 

    # Plot each product line
    plt.plot(deductibles, mtpl, label='MTPL (Baseline)', marker='s', linestyle='--', color='gray')
    plt.plot(deductibles, limited_casco, label='Limited Casco', marker='o', color='orange')
    plt.plot(deductibles, casco, label='Casco', marker='o', color='blue')

    plt.xlabel('Deductible (€)', fontsize=12)
    plt.ylabel('Premium Price (€)', fontsize=12)
    plt.xticks(deductibles) 
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend(fontsize=11)

    plt.tight_layout()
    
def prices_diff_graph(original: dict[str, float], fixed: dict[str, float], title=None) -> None:
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
        ("casco", "Casco", "blue")
    ]

    for key, label, color in products:
        old_vals = get_coords(original, key)
        new_vals = get_coords(fixed, key)
        
        # Plot original prices (dashed, transparent)
        plt.plot(deductibles, old_vals, linestyle='--', marker='x', 
                 color=color, alpha=0.3, label=f"{label} (Original)")
        
        # Plot fixed prices (solid)
        plt.plot(deductibles, new_vals, linestyle='-', marker='o', 
                 color=color, linewidth=2, label=f"{label} (Fixed)")
    
    if not title is None:
        plt.title(title)
        
    plt.xlabel('Deductible (€)', fontsize=12)
    plt.ylabel('Premium Price (€)', fontsize=12)
    plt.xticks(deductibles)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plt.show()



def validate_and_fix_prices(prices: dict[str, float]) -> dict:
    """
    Validates and fixes motor insurance pricing rules.
    Uses a post-processing diff comparison (initial vs. final) to accurately
    report the real, net adjustments made, eliminating intermediate noise.
    """
    # Define proportional adjustments based on the deductible guide.
    RATIO_200_DEDUCTIBLE = 0.85  # Represents roughly -15% relative to 100 EUR base.
    RATIO_500_DEDUCTIBLE = 0.80  # Represents roughly -20% relative to 100 EUR base.
    
    # Ratios derived from average market prices to ensure proportional adjustments.
    RATIO_MTPL_TO_LC = 500 / 900   
    RATIO_CASCO_TO_LC = 1200 / 900 

    initial_prices = prices.copy()
    fixed_prices = prices.copy()
    
    # --- Helper Functions ---
    def round_price(val: float) -> float:
        return round(float(val), 2)
    
    def is_valid_sequence(price_100: float, price_200: float, price_500: float) -> bool:
        # A higher deductible means a lower premium.
        return price_500 < price_200 < price_100

    def optimize_deductibles(product_prefix: str, lower_bounds: dict = None):
        price_100 = fixed_prices[f"{product_prefix}_100"]
        price_200 = fixed_prices[f"{product_prefix}_200"]
        price_500 = fixed_prices[f"{product_prefix}_500"]
        
        # If the pricing rules are already respected, keep the prices as ground truth.
        if is_valid_sequence(price_100, price_200, price_500):
            return
            
        candidates = []
        lower_bounds = lower_bounds or {}
        
        # Keep fixes minimal by testing single-price adjustments first.
        
        # Scenario A1: Fix 100 EUR deductible based on the 200 EUR price
        new_100_from_200 = round_price(price_200 / RATIO_200_DEDUCTIBLE)
        if is_valid_sequence(new_100_from_200, price_200, price_500) and new_100_from_200 > lower_bounds.get("100", 0):
            candidates.append((abs(new_100_from_200 - price_100), new_100_from_200, price_200, price_500))

        # Scenario A2: Fix 100 EUR deductible based on the 500 EUR price
        new_100_from_500 = round_price(price_500 / RATIO_500_DEDUCTIBLE)
        if is_valid_sequence(new_100_from_500, price_200, price_500) and new_100_from_500 > lower_bounds.get("100", 0):
            candidates.append((abs(new_100_from_500 - price_100), new_100_from_500, price_200, price_500))
            
        # Scenario B: Fix only the 200 EUR deductible
        new_200 = round_price(price_100 * RATIO_200_DEDUCTIBLE)
        if is_valid_sequence(price_100, new_200, price_500) and new_200 > lower_bounds.get("200", 0):
            candidates.append((abs(new_200 - price_200), price_100, new_200, price_500))
            
        # Scenario C: Fix only the 500 EUR deductible
        new_500 = round_price(price_100 * RATIO_500_DEDUCTIBLE)
        if is_valid_sequence(price_100, price_200, new_500) and new_500 > lower_bounds.get("500", 0):
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
        adjusted_mtpl = round_price(fixed_prices["limited_casco_100"] * RATIO_MTPL_TO_LC)
        
        # Ensure the proportional scaling didn't overshoot the closest tier
        # If so, adjust MTPL based on the LC500 price transformed into LC100
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
            if deductible == "200": upper_bound = fixed_prices["casco_100"]
            if deductible == "500": upper_bound = fixed_prices["casco_200"]
            
            if upper_bound and new_casco_price >= upper_bound:
                if lc_price < upper_bound:
                    new_casco_price = round_price((lc_price + upper_bound) / 2)
                else:
                    new_casco_price = round_price(lc_price * 1.05)
                    
            fixed_prices[f"casco_{deductible}"] = new_casco_price
            
    # Hierarchy failsafe to verify internal Casco ordering after hierarchy adjustments
    if not is_valid_sequence(fixed_prices["casco_100"], fixed_prices["casco_200"], fixed_prices["casco_500"]):
        casco_lower_bounds = {
            "100": fixed_prices["limited_casco_100"],
            "200": fixed_prices["limited_casco_200"],
            "500": fixed_prices["limited_casco_500"]
        }
        optimize_deductibles("casco", lower_bounds=casco_lower_bounds)
        
    # Generate explanations for automatically fixed violations in plain language.
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
                reasons.append(f"Casco must be more expensive than Limited Casco at the {deductible_tier}€ deductible")
        
        if key != "mtpl":
            prefix = "limited_casco" if "limited" in key else "casco"
            orig_100 = initial_prices[f"{prefix}_100"]
            orig_200 = initial_prices[f"{prefix}_200"]
            orig_500 = initial_prices[f"{prefix}_500"]
            
            if not is_valid_sequence(orig_100, orig_200, orig_500):
                reasons.append("the internal deductible ordering was invalid (higher deductibles must cost less)")
                
        reason_string = " and ".join(reasons) if reasons else "to resolve overlapping pricing violations caused by adjusting other products"
        issues.append(f"Adjusted '{key}' from {initial_val} to {final_val} because {reason_string}.")

    # Return exactly the expected dictionary format.
    return {
        "fixed_prices": fixed_prices,
        "issues": issues
    }


def run_unit_tests(test_cases: dict[str, dict], details=True, show_graphs=False):
    print("--- RUNNING EDGE CASE TESTS ---\n")
    for ind, (test_name, test_data) in enumerate(test_cases.items()):
        
        prices = test_data["prices"]
        expected_issues = test_data["expected_issues"]
        
        print(f"=== {ind+1}. {test_name} ===")
        result = validate_and_fix_prices(prices)
        issues_returned = result["issues"]
        actual_issues = len(issues_returned)
        
        if details:
            print(f"Input:  {prices}")
            print(f"Output: {result['fixed_prices']}")
            print(f"Expected Issues: {expected_issues} | Actual Issues: {actual_issues}")
            print("Issues Fixed:")
            if not issues_returned:
                print("  - None (Perfect!)")
            else:
                for issue in issues_returned:
                    print(f"  - {issue}")
        
        # Validation checks
        fp = result["fixed_prices"]
        is_prices_valid = (
            fp["mtpl"] < fp["limited_casco_500"] and
            fp["limited_casco_500"] < fp["limited_casco_200"] < fp["limited_casco_100"] and
            fp["casco_500"] < fp["casco_200"] < fp["casco_100"] and
            all(fp[f"casco_{d}"] > fp[f"limited_casco_{d}"] for d in ["100", "200", "500"])
        )
        is_step_count_valid = (actual_issues == expected_issues)
        
        if is_prices_valid and is_step_count_valid:
            print("Verdict: ✅ PASSED\n")
        else:
            print("Verdict: ❌ FAILED")
            if not is_prices_valid:
                print("  -> Reason: Math/hierarchy validation failed.")
            if not is_step_count_valid:
                print(f"  -> Reason: Step count mismatch (Expected {expected_issues}, Got {actual_issues}).")
            print("\n")
        
        if show_graphs:
            prices_diff_graph(prices, fp, title=f"{ind+1}. {test_name}")


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
            "expected_issues": 2
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
            "expected_issues": 2
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
            "expected_issues": 0
        },
        "Completely Inverted Hierarchy": {
            "prices": {
                "mtpl": 1500,        # MTPL is the most expensive
                "limited_casco_100": 1000,
                "limited_casco_200": 900,
                "limited_casco_500": 800,
                "casco_100": 500,    # Casco is the cheapest
                "casco_200": 400,
                "casco_500": 300,
            },
            "expected_issues": 4
        },
        "Completely Inverted Deductibles": {
            "prices": {
                "mtpl": 300,
                "limited_casco_100": 700,
                "limited_casco_200": 800, # Higher deductible costs more
                "limited_casco_500": 900, # Highest deductible costs most
                "casco_100": 1000,
                "casco_200": 1100,
                "casco_500": 1200,
            },
            "expected_issues": 4
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
            "expected_issues": 6
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
            "expected_issues": 5
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
            "expected_issues": 4
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
            "expected_issues": 1
        }
    }
    
    run_unit_tests(test_cases, details=False, show_graphs=True)