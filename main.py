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
    initial_prices = prices.copy()
    fixed = prices.copy()
    
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
                candidates.append((abs(np1 - p1), "100", np1, p2, p5))
            
        # Scenario 2: Try fixing ONLY the 200 deductible (-15% guide)
        np2 = r(p1 * 0.85)
        if p5 < np2 < p1:
            if not lower_bounds or np2 > lower_bounds.get("200", 0):
                candidates.append((abs(np2 - p2), "200", p1, np2, p5))
            
        # Scenario 3: Try fixing ONLY the 500 deductible (-20% guide)
        np5 = r(p1 * 0.80)
        if np5 < p2 < p1:
            if not lower_bounds or np5 > lower_bounds.get("500", 0):
                candidates.append((abs(np5 - p5), "500", p1, p2, np5))
            
        # Apply the minimal fix
        if candidates:
            candidates.sort(key=lambda x: x[0])
            _, _, v1, v2, v5 = candidates[0]
            fixed[f"{prefix}_100"] = v1
            fixed[f"{prefix}_200"] = v2
            fixed[f"{prefix}_500"] = v5
        else:
            # Failsafe for severe multi-price corruption
            base = p1
            if lower_bounds and base <= lower_bounds.get("100", 0):
                base = lower_bounds.get("100", 0) + 50 

            nv2 = r(base * 0.85)
            nv5 = r(base * 0.80)

            if lower_bounds and nv2 <= lower_bounds.get("200", 0):
                nv2 = lower_bounds.get("200", 0) + 10
            if lower_bounds and nv5 <= lower_bounds.get("500", 0):
                nv5 = lower_bounds.get("500", 0) + 10

            fixed[f"{prefix}_100"] = base
            fixed[f"{prefix}_200"] = nv2
            fixed[f"{prefix}_500"] = nv5

    # --- 1. Optimize Internal Deductibles first ---
    optimize_deductibles("limited_casco")
    optimize_deductibles("casco")
    
    # --- 2. Enforce Hierarchy between products ---
    if fixed["mtpl"] >= fixed["limited_casco_500"]:
        new_mtpl = r(fixed["limited_casco_100"] * (500 / 900))
        if new_mtpl >= fixed["limited_casco_500"]:
            new_mtpl = r(fixed["limited_casco_500"] * 0.90)
        fixed["mtpl"] = new_mtpl
        
    for ded in ["100", "200", "500"]:
        lc_val = fixed[f"limited_casco_{ded}"]
        c_val = fixed[f"casco_{ded}"]
        
        if c_val <= lc_val:
            new_c = r(lc_val * (1200 / 900))
            
            # Squeeze logic
            upper_bound = None
            if ded == "200": upper_bound = fixed["casco_100"]
            if ded == "500": upper_bound = fixed["casco_200"]
            
            if upper_bound and new_c >= upper_bound:
                if lc_val < upper_bound:
                    new_c = r((lc_val + upper_bound) / 2)
                else:
                    new_c = r(lc_val * 1.05)
                    
            fixed[f"casco_{ded}"] = new_c
            
    # --- 3. Final Failsafe ---
    p1, p2, p5 = fixed["casco_100"], fixed["casco_200"], fixed["casco_500"]
    if not (p5 < p2 < p1):
        casco_bounds = {
            "100": fixed["limited_casco_100"],
            "200": fixed["limited_casco_200"],
            "500": fixed["limited_casco_500"]
        }
        optimize_deductibles("casco", lower_bounds=casco_bounds)
        
    # ==========================================
    # --- NEW: POST-PROCESSING ISSUES SYSTEM ---
    # ==========================================
    issues = []
    for key, initial_val in initial_prices.items():
        final_val = fixed[key]
        
        # Only log an issue if the net price actually changed
        if initial_val != final_val:
            reasons = []
            
            # Infer the reason by looking at what was wrong in the INITIAL state
            if key == "mtpl" and initial_val >= initial_prices["limited_casco_500"]:
                reasons.append("MTPL must be cheaper than Limited Casco")
                
            if "casco" in key and "limited" not in key:
                ded = key.split("_")[1]
                if initial_val <= initial_prices[f"limited_casco_{ded}"]:
                    reasons.append(f"Casco must be more expensive than Limited Casco at the {ded} deductible")
            
            if key != "mtpl":
                prefix = "limited_casco" if "limited" in key else "casco"
                p1, p2, p5 = initial_prices[f"{prefix}_100"], initial_prices[f"{prefix}_200"], initial_prices[f"{prefix}_500"]
                if not (p5 < p2 < p1):
                    reasons.append("the internal deductible sequence was corrupted")
                    
            # If a price was changed purely as a side-effect (failsafe/cascade) and had no direct violations originally:
            reason_str = " and ".join(reasons) if reasons else "to resolve overlapping pricing violations from a cascade"
            
            issues.append(f"Adjusted '{key}' from {initial_val} to {final_val} because {reason_str}.")

    return {
        "fixed_prices": fixed,
        "issues": issues
    }


def run_unit_tests(test_cases : dict[str, dict[str, float]], details=True, show_graphs=False):
    print("--- RUNNING EDGE CASE TESTS ---\n")
    for ind, test in enumerate(test_cases.items()):
        test_name, prices = test
        
        print(f"=== {ind+1}.{test_name} ===")
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
        
        print(f"Verdict: {'✅ PASSED' if is_valid else '❌ FAILED'}\n")
        
        if show_graphs:
            prices_diff_graph(prices, fp, title=f"{ind+1}.{test_name}")


if __name__ == "__main__":
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
    
    run_unit_tests(test_cases, details=True, show_graphs=True)
    