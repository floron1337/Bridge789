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
    
def prices_diff_graph(original: dict[str, float], fixed: dict[str, float]) -> None:
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
    Identifies and targets single-point anomalies to guarantee the minimum number of adjustments,
    while strictly enforcing product hierarchy bounds and preventing unnecessary cascades.
    """
    fixed = prices.copy()
    issues = []
    
    def r(val): return round(float(val), 2)
    
    def optimize_deductibles(prefix, lower_bounds=None):
        p1 = fixed[f"{prefix}_100"]
        p2 = fixed[f"{prefix}_200"]
        p5 = fixed[f"{prefix}_500"]
        
        # If sequence is already perfectly valid, touch nothing
        if p5 < p2 < p1:
            return
            
        candidates = []
        
        # Scenario 1: Try fixing ONLY the 100 deductible
        np1 = r(p2 / 0.85)
        if p5 < p2 < np1:
            if not lower_bounds or np1 > lower_bounds.get("100", 0):
                candidates.append((abs(np1 - p1), "100", np1, p2, p5, f"Fixed {prefix}_100: Adjusted {p1} -> {np1} to restore sequence."))
            
        # Scenario 2: Try fixing ONLY the 200 deductible (-15% guide)
        np2 = r(p1 * 0.85)
        if p5 < np2 < p1:
            if not lower_bounds or np2 > lower_bounds.get("200", 0):
                candidates.append((abs(np2 - p2), "200", p1, np2, p5, f"Fixed {prefix}_200: Adjusted {p2} -> {np2} using -15% guide."))
            
        # Scenario 3: Try fixing ONLY the 500 deductible (-20% guide)
        np5 = r(p1 * 0.80)
        if np5 < p2 < p1:
            if not lower_bounds or np5 > lower_bounds.get("500", 0):
                candidates.append((abs(np5 - p5), "500", p1, p2, np5, f"Fixed {prefix}_500: Adjusted {p5} -> {np5} using -20% guide."))
            
        # If a single-price fix works, pick the one that alters the original price the least
        if candidates:
            candidates.sort(key=lambda x: x[0])
            _, fixed_ded, v1, v2, v5, msg = candidates[0]
            fixed[f"{prefix}_100"] = v1
            fixed[f"{prefix}_200"] = v2
            fixed[f"{prefix}_500"] = v5
            issues.append(msg)
        else:
            # Failsafe for severe multi-price corruption
            base = p1
            if lower_bounds and base <= lower_bounds.get("100", 0):
                base = lower_bounds.get("100", 0) + 50 # Bump base safely above lower bound
                fixed[f"{prefix}_100"] = base
                issues.append(f"Fixed {prefix}_100: Bumped base to {base} to clear lower bound.")

            nv2 = r(base * 0.85)
            nv5 = r(base * 0.80)

            # Ensure derived bounds don't violate hierarchy
            if lower_bounds and nv2 <= lower_bounds.get("200", 0):
                nv2 = lower_bounds.get("200", 0) + 10
            if lower_bounds and nv5 <= lower_bounds.get("500", 0):
                nv5 = lower_bounds.get("500", 0) + 10

            fixed[f"{prefix}_200"] = nv2
            fixed[f"{prefix}_500"] = nv5
            issues.append(f"Fixed {prefix}_200 and 500: Reset based on 100 base to restore sequence, respecting limits.")

    # 1. Optimize Internal Deductibles first
    optimize_deductibles("limited_casco")
    optimize_deductibles("casco")
    
    # 2. Enforce Hierarchy between products
    # MTPL must be cheaper than Limited Casco (strictest bound is the 500 deductible)
    if fixed["mtpl"] >= fixed["limited_casco_500"]:
        old_mtpl = fixed["mtpl"]
        # Proportional fix using the provided real market averages (MTPL: 500, LC: 900 -> 5/9 ratio)
        new_mtpl = r(fixed["limited_casco_100"] * (500 / 900))
        # Ensure it actually drops safely below the 500 deductible tier
        if new_mtpl >= fixed["limited_casco_500"]:
            new_mtpl = r(fixed["limited_casco_500"] * 0.90)
        fixed["mtpl"] = new_mtpl
        issues.append(f"Fixed mtpl: Violated hierarchy (>= limited_casco_500). Adjusted {old_mtpl} -> {new_mtpl} using market ratio.")
        
    # Casco must be more expensive than Limited Casco at every level
    for ded in ["100", "200", "500"]:
        lc_val = fixed[f"limited_casco_{ded}"]
        c_val = fixed[f"casco_{ded}"]
        
        if c_val <= lc_val:
            old_c = c_val
            # Proportional fix using the provided real market averages (Casco: 1200, LC: 900 -> 12/9 ratio)
            new_c = r(lc_val * (1200 / 900))
            
            # Context-aware bounding: prevent the fix from unnecessarily breaking the Casco sequence
            upper_bound = None
            if ded == "200": upper_bound = fixed["casco_100"]
            if ded == "500": upper_bound = fixed["casco_200"]
            
            if upper_bound and new_c >= upper_bound:
                if lc_val < upper_bound:
                    # Squeeze it safely halfway between limited casco and the upper casco tier
                    new_c = r((lc_val + upper_bound) / 2)
                else:
                    # Squeeze is impossible; bump slightly and let the failsafe handle the severe corruption
                    new_c = r(lc_val * 1.05)
                    
            fixed[f"casco_{ded}"] = new_c
            issues.append(f"Fixed casco_{ded}: Violated hierarchy (<= limited_casco_{ded}). Adjusted {old_c} -> {new_c} safely.")
            
    # 3. Final Failsafe: Re-verify Casco deductibles in case a hierarchy bump inverted them
    p1, p2, p5 = fixed["casco_100"], fixed["casco_200"], fixed["casco_500"]
    if not (p5 < p2 < p1):
        # Pass the limited_casco prices as the lower bounds to prevent recursive violations
        casco_bounds = {
            "100": fixed["limited_casco_100"],
            "200": fixed["limited_casco_200"],
            "500": fixed["limited_casco_500"]
        }
        optimize_deductibles("casco", lower_bounds=casco_bounds)
        
    return {
        "fixed_prices": fixed,
        "issues": issues
    }

if __name__ == "__main__":
    details = False
    
    test_cases = {
        "Problem Example: " : {
            "mtpl": 400,
            "limited_casco_100": 850,
            "limited_casco_200": 900,
            "limited_casco_500": 700,
            "casco_100": 780,
            "casco_200": 950,
            "casco_500": 830,
        },
        "The Original Edge Case (Squeeze Logic)": {
            "mtpl": 1000,
            "limited_casco_100": 950,
            "limited_casco_200": 900,
            "limited_casco_500": 500,
            "casco_100": 1000,
            "casco_200": 800,  # Fails hierarchy
            "casco_500": 600,
        },
        "Perfect Input (Should touch nothing)": {
            "mtpl": 400,
            "limited_casco_100": 850,
            "limited_casco_200": 720,
            "limited_casco_500": 680,
            "casco_100": 1200,
            "casco_200": 1020,
            "casco_500": 960,
        },
        "Completely Inverted Hierarchy": {
            "mtpl": 1500,        # MTPL is the most expensive
            "limited_casco_100": 1000,
            "limited_casco_200": 900,
            "limited_casco_500": 800,
            "casco_100": 500,    # Casco is the cheapest
            "casco_200": 400,
            "casco_500": 300,
        },
        "Completely Inverted Deductibles": {
            "mtpl": 300,
            "limited_casco_100": 700,
            "limited_casco_200": 800, # Higher deductible costs more
            "limited_casco_500": 900, # Highest deductible costs most
            "casco_100": 1000,
            "casco_200": 1100,
            "casco_500": 1200,
        },
        "Flat Pricing (Equal values)": {
            "mtpl": 800,
            "limited_casco_100": 800,
            "limited_casco_200": 800,
            "limited_casco_500": 800,
            "casco_100": 800,
            "casco_200": 800,
            "casco_500": 800,
        },
        "Severe Multi-Price Corruption (Chaos)": {
            "mtpl": 9999,
            "limited_casco_100": 10,
            "limited_casco_200": 5000,
            "limited_casco_500": 20,
            "casco_100": 15,
            "casco_200": 6000,
            "casco_500": 5,
        }
    }

    print("--- RUNNING EDGE CASE TESTS ---\n")
    for test_name, prices in test_cases.items():
        print(f"=== {test_name} ===")
        result = validate_and_fix_prices(prices)
        
        if details:
            print(f"Input:  {prices}")
            print(f"Output: {result['fixed_prices']}")
            print("Issues Fixed:")
            if not result["issues"]:
                print("  - None (Perfect!)")
            else:
                for issue in result["issues"]:
                    print(f"  - {issue}")
        
        # Quick validation check of the output
        fp = result["fixed_prices"]
        is_valid = (
            fp["mtpl"] < fp["limited_casco_500"] and
            fp["limited_casco_500"] < fp["limited_casco_200"] < fp["limited_casco_100"] and
            fp["casco_500"] < fp["casco_200"] < fp["casco_100"] and
            all(fp[f"casco_{d}"] > fp[f"limited_casco_{d}"] for d in ["100", "200", "500"])
        )
        
        print(f"Final State Valid: {'✅ YES' if is_valid else '❌ NO'}\n")
        
        prices_diff_graph(prices, fp)