import json

# Extracting driver data:
with open("driver_info.json") as f:
    driver_info = json.load(f)

# Extracting login data:
with open("login_info.json") as f:
    login_info = json.load(f)

# Extracting navigation data:
with open("navigation_map.json") as f:
    nav_map = json.load(f)

# Extracting htlm keys:
with open("html_keys.json") as f:
    htmlk = json.load(f)
