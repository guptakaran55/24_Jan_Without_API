# compare_methods.py
import json
from ramp.core.core import User, ApplianceLoader

# Load your JSON
from tkinter import Tk, filedialog
root = Tk(); root.withdraw(); root.attributes('-topmost', True)
json_file = filedialog.askopenfilename(title="Select JSON", filetypes=[("JSON","*.json")])
if not json_file: exit()

with open(json_file, 'r') as f:
    data = json.load(f)

# ─── Method 1: ApplianceLoader (original) ───
HH1 = User(user_name="original", num_users=1, user_preference=3)
loader = ApplianceLoader(HH1)
loader.load_from_json(json_file)

# ─── Method 2: add_appliance (our way) ───
HH2 = User(user_name="ours", num_users=1, user_preference=3)
for app_data in data.get('appliances', []):
    fixed_raw = app_data.get('fixed', 'no')
    if isinstance(fixed_raw, int): fixed_val = fixed_raw
    elif str(fixed_raw).lower() in ('yes','1','true'): fixed_val = 1
    else: fixed_val = 0
    
    kwargs = dict(
        name=app_data.get('name','?'), number=int(app_data.get('number',1)),
        power=int(app_data.get('power',100)), func_time=int(app_data.get('func_time',60)),
        func_cycle=int(app_data.get('func_cycle',1)), num_windows=int(app_data.get('num_windows',1)),
        wd_we_type=int(app_data.get('wd_we_type',2)), fixed=fixed_val, flat=0,
        occasional_use=float(app_data.get('occasional_use',1.0)),
        random_var_w=float(app_data.get('random_var_w',0.35)),
        time_fraction_random_variability=float(app_data.get('time_fraction_random_variability',0.2)),
    )
    w1 = app_data.get('window_1')
    if w1 and len(w1)==2 and w1[0] is not None: kwargs['window_1'] = w1
    else: kwargs['window_1'] = [0,1440]
    w2 = app_data.get('window_2')
    if w2 and len(w2)==2 and w2[0] is not None: kwargs['window_2'] = w2
    w3 = app_data.get('window_3')
    if w3 and len(w3)==2 and w3[0] is not None: kwargs['window_3'] = w3
    HH2.add_appliance(**kwargs)

# ─── Compare ───
attrs = ['name','number','power','func_time','func_cycle','num_windows',
         'fixed','flat','fixed_cycle','occasional_use','wd_we_type',
         'time_fraction_random_variability','random_var_w',
         'window_1','window_2','window_3','random_var_w']

print(f"\n{'ATTRIBUTE':<40} {'ORIGINAL':<20} {'OURS':<20} {'MATCH'}")
print("=" * 100)
for a1, a2 in zip(HH1.App_list, HH2.App_list):
    print(f"\n>>> {a1.name} vs {a2.name}")
    print("-" * 100)
    for attr in attrs:
        v1 = getattr(a1, attr, '???')
        v2 = getattr(a2, attr, '???')
        match = "✓" if str(v1) == str(v2) else "✗ DIFF"
        if str(v1) != str(v2):
            print(f"  {attr:<38} {str(v1):<20} {str(v2):<20} {match}")
    # Check if all match
    diffs = sum(1 for attr in attrs if str(getattr(a1,attr,'?')) != str(getattr(a2,attr,'?')))
    if diffs == 0:
        print(f"  All attributes match ✓")