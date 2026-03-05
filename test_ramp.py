# test_ramp.py
# Quick test: pick a survey JSON file → run RAMP simulation → show output
# Usage: python test_ramp.py
#    or: python test_ramp.py path/to/survey.json

import sys
import json

def main():
    # ── Get JSON file path ──────────────────────────────────────────
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    else:
        try:
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            json_path = filedialog.askopenfilename(
                title="Select Survey JSON file",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialdir="."
            )
            if not json_path:
                print("No file selected. Exiting.")
                return
        except ImportError:
            json_path = input("Enter path to survey JSON file: ").strip().strip('"')
            if not json_path:
                print("No path entered. Exiting.")
                return

    # ── Load JSON ───────────────────────────────────────────────────
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            survey_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {json_path}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return

    appliances = survey_data.get('appliances', [])
    print(f"\n📂 Loaded: {json_path}")
    print(f"   Appliances found: {len(appliances)}")

    if not appliances:
        print("❌ No appliances in this JSON. Nothing to simulate.")
        return

    # ── Preview appliances ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"{'#':<3} {'Name':<22} {'Qty':<4} {'Power':<8} {'Hours/day':<10} {'Window 1'}")
    print("-" * 70)
    for i, a in enumerate(appliances, 1):
        name = a.get('name', '?')[:21]
        qty = a.get('number', 1)
        power = f"{a.get('power', '?')}W"
        ft = a.get('func_time', 0)
        hours = f"{ft / 60:.1f}h" if ft else "?"
        w1 = a.get('window_1')
        if w1 and len(w1) == 2 and w1[0] is not None:
            w_str = f"{w1[0]//60:02d}:{w1[0]%60:02d}-{w1[1]//60:02d}:{w1[1]%60:02d}"
        else:
            w_str = "anytime"
        print(f"{i:<3} {name:<22} {qty:<4} {power:<8} {hours:<10} {w_str}")

    total_kwh = sum(
        a.get('power', 0) * a.get('number', 1) * a.get('func_time', 0) / 60 / 1000
        for a in appliances
    )
    print("-" * 70)
    print(f"{'Estimated daily energy:':<48} {total_kwh:.2f} kWh")
    print("=" * 70)

    # ── Run RAMP simulation ─────────────────────────────────────────
    # RAMP will ask for number of days to simulate itself
    try:
        from ramp_simulation import run_ramp_simulation
    except ImportError:
        print("\n❌ Could not import ramp_simulation.py")
        print("   Make sure ramp_simulation.py is in the same folder as this script.")
        return

    result = run_ramp_simulation(
        survey_data,
        show_plot=True
    )

    if result.get('success'):
        print("\n✅ Done! Close the plot window(s) to exit.")
    else:
        print(f"\n❌ Simulation failed: {result.get('error', 'Unknown')}")


if __name__ == "__main__":
    main()