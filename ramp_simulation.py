# ramp_simulation.py
# Converts survey JSON appliance data into RAMP simulation inputs
# and generates daily electricity consumption profiles.
#
# MATCHES the ApplianceLoader approach exactly:
#   1. add_appliance() with core params only (no windows, no fixed, no wd_we_type)
#   2. Set optional attributes directly on the appliance object
#   3. Call .windows() separately with keyword args

import json
import os
import sys
import numpy as np


def _check_ramp_installed():
    """Check if RAMP is installed and return True/False."""
    try:
        from ramp.core.core import User, UseCase
        return True
    except ImportError:
        return False


def convert_survey_to_ramp_appliances(survey_data):
    """
    Convert survey JSON appliance data into RAMP User + Appliance objects.
    Mirrors the ApplianceLoader.add_appliance_from_dict() method exactly.
    """
    from ramp.core.core import User

    User_list = []
    HH = User(user_name="survey_household", num_users=1, user_preference=3)
    User_list.append(HH)

    appliances = survey_data.get('appliances', [])
    if not appliances:
        print("⚠️  No appliances found in survey data.")
        return User_list

    for i, config in enumerate(appliances):
        name = config.get('name', f'Appliance_{i+1}')
        number = config.get('number', 1)
        power = config.get('power', 100)
        func_time = config.get('func_time', 60)
        num_windows = config.get('num_windows', 1)
        func_cycle = config.get('func_cycle', 1)

        # Optional parameters with defaults (matching ApplianceLoader)
        time_fraction_random_variability = config.get('time_fraction_random_variability', 0.2)
        thermal_p_var = config.get('thermal_p_var', 0.1)
        pref_index = config.get('pref_index', 0)

        # Additional RAMP parameters (matching ApplianceLoader defaults)
        occasional_use = config.get('occasional_use', 1.0)
        fixed = config.get('fixed', 'no')
        wd_we_type = config.get('wd_we_type', 0)  # ApplianceLoader defaults to 0, not 2

        # ─── Step 1: add_appliance with CORE params only ───
        # (exactly matching ApplianceLoader.add_appliance_from_dict)
        try:
            appliance = HH.add_appliance(
                number=number,
                power=power,
                num_windows=num_windows,
                func_time=func_time,
                time_fraction_random_variability=time_fraction_random_variability,
                func_cycle=func_cycle,
                thermal_p_var=thermal_p_var,
                pref_index=pref_index,
                name=name,
            )
        except Exception as e:
            print(f"   ⚠️  Failed to create '{name}': {e}")
            continue

        # ─── Step 2: Set additional attributes directly ───
        # (exactly matching ApplianceLoader)
        if hasattr(appliance, 'occasional_use'):
            appliance.occasional_use = occasional_use
        if hasattr(appliance, 'fixed') and fixed:
            appliance.fixed = fixed
        if hasattr(appliance, 'wd_we_type'):
            appliance.wd_we_type = wd_we_type

        # ─── Step 3: Add windows via .windows() call ───
        # (exactly matching ApplianceLoader._add_windows)
        random_var_w = config.get('random_var_w', 0.2)

        windows = []
        for wi in range(1, num_windows + 1):
            window_key = f'window_{wi}'
            if window_key in config and config[window_key] is not None:
                w = config[window_key]
                if len(w) == 2 and w[0] is not None:
                    windows.append(w)

        try:
            if num_windows == 1 and len(windows) >= 1:
                appliance.windows(
                    window_1=windows[0],
                    random_var_w=random_var_w,
                )
            elif num_windows == 2 and len(windows) >= 2:
                appliance.windows(
                    window_1=windows[0],
                    window_2=windows[1],
                    random_var_w=random_var_w,
                )
            elif num_windows == 3 and len(windows) >= 3:
                appliance.windows(
                    window_1=windows[0],
                    window_2=windows[1],
                    window_3=windows[2],
                    random_var_w=random_var_w,
                )
            elif len(windows) >= 1:
                # Fallback: at least set window_1
                appliance.windows(
                    window_1=windows[0],
                    random_var_w=random_var_w,
                )
            else:
                # No windows specified, use full day
                appliance.windows(
                    window_1=[0, 1440],
                    random_var_w=random_var_w,
                )
        except Exception as e:
            print(f"   ⚠️  Failed to set windows for '{name}': {e}")
            # Try fallback
            try:
                appliance.windows(window_1=[0, 1440], random_var_w=random_var_w)
            except Exception:
                pass

        print(f"   ✓ Added: {name} ({number}x, {power}W, {func_time}min/day, fixed={fixed})")

    return User_list


def run_ramp_simulation(survey_data, num_profiles=1, peak_enlarge=0.15, show_plot=True):
    """
    Run the RAMP simulation using survey data.

    Args:
        survey_data: dict with 'appliances' list
        num_profiles: int, number of daily profiles to simulate
        peak_enlarge: float, peak enlargement factor
        show_plot: bool, whether to show matplotlib plots

    Returns:
        dict with simulation results
    """
    if not _check_ramp_installed():
        print("\n❌ RAMP is not installed.")
        print("   Install it with: pip install ramp-demand")
        return {'success': False, 'error': 'RAMP not installed'}

    from ramp.core.core import UseCase

    print("\n" + "=" * 80)
    print("⚡ RAMP SIMULATION — Generating Electricity Consumption Profile")
    print("=" * 80)

    print(f"\n📋 Converting {len(survey_data.get('appliances', []))} appliance(s) to RAMP format...")
    User_list = convert_survey_to_ramp_appliances(survey_data)

    total_appliances = sum(len(u.App_list) for u in User_list)
    if total_appliances == 0:
        print("\n⚠️  No appliances could be converted. Skipping simulation.")
        return {'success': False, 'error': 'No appliances converted'}

    print(f"\n🔧 Running simulation with {total_appliances} appliance(s), {num_profiles} profile(s)...")

    try:
        uc = UseCase(users=User_list, parallel_processing=False)
        uc.initialize(peak_enlarge=peak_enlarge)
        Profiles_list = uc.generate_daily_load_profiles(flat=False)

        from ramp.post_process import post_process as pp
        Profiles_avg, Profiles_list_kW, Profiles_series = pp.Profile_formatting(Profiles_list)

        print(f"\n✅ Simulation complete!")
        print(f"   Profiles generated: {len(Profiles_list)}")

        if Profiles_avg is not None and len(Profiles_avg) > 0:
            peak_w = np.max(Profiles_avg)
            avg_w = np.mean(Profiles_avg)
            total_kwh = np.sum(Profiles_avg) / (60 * 1000)
            print(f"   Peak demand: {peak_w:.0f} W")
            print(f"   Average demand: {avg_w:.0f} W")
            print(f"   Total daily energy: {total_kwh:.2f} kWh")

        if show_plot:
            print("\n📊 Generating plots...")
            try:
                pp.Profile_series_plot(Profiles_series)
                if len(Profiles_list) > 1:
                    pp.Profile_cloud_plot(Profiles_list, Profiles_avg)
            except Exception as plot_err:
                print(f"   ⚠️  Plotting failed: {plot_err}")

        return {
            'success': True,
            'Profiles_list': Profiles_list,
            'Profiles_avg': Profiles_avg,
            'Profiles_list_kW': Profiles_list_kW,
            'Profiles_series': Profiles_series,
        }

    except Exception as e:
        print(f"\n❌ RAMP simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def run_ramp_from_json_file(json_filepath, num_profiles=1, show_plot=True):
    """Load a survey JSON file and run the RAMP simulation."""
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            survey_data = json.load(f)
        print(f"📂 Loaded survey data from: {json_filepath}")
        return run_ramp_simulation(survey_data, num_profiles=num_profiles, show_plot=show_plot)
    except FileNotFoundError:
        print(f"❌ File not found: {json_filepath}")
        return {'success': False, 'error': 'File not found'}
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in file: {e}")
        return {'success': False, 'error': f'Invalid JSON: {e}'}


if __name__ == "__main__":
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
                print("No file selected. Exiting...")
                sys.exit()
        except ImportError:
            print("Usage: python ramp_simulation.py <path_to_survey_json>")
            sys.exit(1)

    result = run_ramp_from_json_file(json_path, num_profiles=1, show_plot=True)
    if result['success']:
        print("\n✅ Simulation finished successfully!")
    else:
        print(f"\n❌ Simulation failed: {result.get('error', 'Unknown error')}")