# ramp_debug.py
# Run this to discover the exact RAMP API signatures on your machine.
# Usage: python ramp_debug.py
#
# Then paste the output back to me so I can fix ramp_simulation.py

import inspect
import sys

print("=" * 70)
print("RAMP API DIAGNOSTIC")
print("=" * 70)

try:
    import ramp
    print(f"\n✓ RAMP version: {ramp.__version__}")
except Exception as e:
    print(f"\n✓ RAMP imported (no __version__): {e}")

try:
    from ramp.core.core import User, UseCase
    print("✓ Imported User, UseCase from ramp.core.core")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Create a test user
HH = User(user_name="test", num_users=1, user_preference=3)

# ─── Check add_appliance signature ───
print("\n" + "-" * 70)
print("1. add_appliance() SIGNATURE:")
print("-" * 70)
try:
    sig = inspect.signature(HH.add_appliance)
    print(f"   {sig}")
    print("\n   Parameters:")
    for name, param in sig.parameters.items():
        print(f"     {name}: kind={param.kind.name}, default={param.default}")
except Exception as e:
    print(f"   Error: {e}")

# ─── Check legacy Appliance signature ───
print("\n" + "-" * 70)
print("2. Appliance() (legacy) SIGNATURE:")
print("-" * 70)
try:
    sig = inspect.signature(HH.Appliance)
    print(f"   {sig}")
    print("\n   Parameters:")
    for name, param in sig.parameters.items():
        print(f"     {name}: kind={param.kind.name}, default={param.default}")
except Exception as e:
    print(f"   Error: {e}")

# ─── Check .windows() signature ───
print("\n" + "-" * 70)
print("3. appliance.windows() SIGNATURE:")
print("-" * 70)
try:
    # Create a dummy appliance to inspect .windows()
    from ramp.core.core import Appliance
    sig = inspect.signature(Appliance.windows)
    print(f"   {sig}")
    print("\n   Parameters:")
    for name, param in sig.parameters.items():
        print(f"     {name}: kind={param.kind.name}, default={param.default}")
except Exception as e:
    print(f"   Error inspecting Appliance.windows: {e}")
    # Try alternate approach
    try:
        test_app = HH.add_appliance(name="test", number=1, power=10, func_time=60, num_windows=1)
        sig = inspect.signature(test_app.windows)
        print(f"   (from instance) {sig}")
        for name, param in sig.parameters.items():
            print(f"     {name}: kind={param.kind.name}, default={param.default}")
    except Exception as e2:
        print(f"   Also failed from instance: {e2}")

# ─── Try creating an actual appliance both ways ───
print("\n" + "-" * 70)
print("4. TEST: add_appliance with window_1 as list")
print("-" * 70)
try:
    a = HH.add_appliance(
        name="TestList", number=1, power=10, func_time=60,
        num_windows=1, window_1=[480, 600], random_var_w=0.2,
    )
    print(f"   ✓ SUCCESS with plain list")
except Exception as e:
    print(f"   ✗ FAILED: {e}")

print("\n" + "-" * 70)
print("5. TEST: add_appliance with window_1 as np.array")
print("-" * 70)
import numpy as np
try:
    a = HH.add_appliance(
        name="TestArray", number=1, power=10, func_time=60,
        num_windows=1, window_1=np.array([480, 600]), random_var_w=0.2,
    )
    print(f"   ✓ SUCCESS with np.array")
except Exception as e:
    print(f"   ✗ FAILED: {e}")

print("\n" + "-" * 70)
print("6. TEST: add_appliance WITHOUT window (then .windows() separately)")
print("-" * 70)
try:
    a = HH.add_appliance(
        name="TestNoWin", number=1, power=10, func_time=60, num_windows=1,
    )
    print(f"   ✓ add_appliance without window succeeded")
    # Now try .windows()
    try:
        a.windows(window_1=[480, 600], random_var_w=0.2)
        print(f"   ✓ .windows(window_1=list, random_var_w=0.2) succeeded")
    except Exception as e:
        print(f"   ✗ .windows() with kwargs failed: {e}")
        try:
            a.windows([480, 600], [0, 0], 0.2)
            print(f"   ✓ .windows(list, list, float) positional succeeded")
        except Exception as e2:
            print(f"   ✗ .windows() positional also failed: {e2}")
            try:
                a.windows(np.array([480, 600]), np.array([0, 0]), 0.2)
                print(f"   ✓ .windows(np.array, np.array, float) succeeded")
            except Exception as e3:
                print(f"   ✗ .windows() with np.array also failed: {e3}")
except Exception as e:
    print(f"   ✗ add_appliance without window failed: {e}")

print("\n" + "-" * 70)
print("7. TEST: Legacy Appliance() + .windows()")
print("-" * 70)
try:
    a = HH.Appliance(HH, 1, 10, 1, 60, 0.2, 1, 0, 1.0, 2)
    print(f"   ✓ Legacy Appliance() with 10 positional args succeeded")
    try:
        a.windows([480, 600], [0, 0], 0.2)
        print(f"   ✓ .windows([list], [list], float) succeeded")
    except Exception as e:
        print(f"   ✗ .windows() failed: {e}")
except Exception as e:
    print(f"   ✗ Legacy Appliance() failed: {e}")
    # Try with fewer args
    try:
        a = HH.Appliance(HH, 1, 10, 1, 60, 0.2, 1)
        print(f"   ✓ Legacy Appliance() with 7 positional args succeeded")
    except Exception as e2:
        print(f"   ✗ Legacy with 7 args also failed: {e2}")

# ─── Appliance class source location ───
print("\n" + "-" * 70)
print("8. SOURCE FILE LOCATIONS:")
print("-" * 70)
try:
    from ramp.core.core import Appliance
    print(f"   Appliance: {inspect.getfile(Appliance)}")
except:
    pass
try:
    print(f"   User: {inspect.getfile(User)}")
except:
    pass

print("\n" + "=" * 70)
print("DONE — Please paste this output back to me!")
print("=" * 70)