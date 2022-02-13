import json
import os


ref_dir = os.path.join(os.getcwd(), 'hattrick_manager', 'reference_data')

# Extracting login data:
with open(os.path.join(ref_dir, 'login_info.json')) as f:
    login_info = json.load(f)

# Extracting navigation data:
with open(os.path.join(ref_dir, 'navigation_map.json')) as f:
    nav_map = json.load(f)

# Extracting htlm keys:
with open(os.path.join(ref_dir, 'html_keys.json')) as f:
    htmlk = json.load(f)

# Extracting team table info:
with open(os.path.join(ref_dir, 'team_table.json')) as f:
    team_table_ref = json.load(f)
