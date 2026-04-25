"""
Day 1 — Config Verification Script
Run:  python verify_config.py
All checks must show ✅ before moving to Day 2.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from internhunter import config as cfg

REQUIRED_KEYS = [
    ("USER_NAME",      cfg.USER_NAME,      "Your full name"),
    ("USER_EMAIL",     cfg.USER_EMAIL,     "your@gmail.com"),
    ("USER_COLLEGE",   cfg.USER_COLLEGE,   "Your college"),
    ("USER_BRANCH",    cfg.USER_BRANCH,    "Your branch"),
    ("USER_YEAR",      cfg.USER_YEAR,      "3rd Year B.Tech"),
    ("USER_SKILLS",    cfg.USER_SKILLS,    ["skill1"]),
    ("USER_GITHUB",    cfg.USER_GITHUB,    "https://github.com/"),
    ("USER_LINKEDIN",  cfg.USER_LINKEDIN,  "https://linkedin.com/"),
    ("SERPER_API_KEY", cfg.SERPER_API_KEY, "your_serper_key"),
    ("GMAIL_USER",     cfg.GMAIL_USER,     "your@gmail.com"),
    ("GMAIL_APP_PASS", cfg.GMAIL_APP_PASS, "16_char_password"),
]

PLACEHOLDERS = {
    "Your Full Name", "you@gmail.com", "IIT/NIT/DTU etc.",
    "Computer Science", "3rd Year B.Tech", "https://github.com/yourhandle",
    "https://linkedin.com/in/yourhandle", "your_serper_api_key_here",
    "your_openai_key_here_optional", "your_16_char_app_password",
    "PASTE_YOUR_SERPER_KEY_HERE", "PASTE_YOUR_16_CHAR_APP_PASSWORD_HERE"
}

print("\n" + "─"*52)
print("  InternHunter AI — Day 1 Config Check")
print("─"*52)

all_ok = True
warnings = []

for key, value, example in REQUIRED_KEYS:
    val_str = ", ".join(value) if isinstance(value, list) else value

    if not value or (isinstance(value, str) and not value.strip()):
        print(f"  ❌  {key:<18} MISSING")
        all_ok = False
    elif isinstance(value, str) and value in PLACEHOLDERS:
        print(f"  ⚠️   {key:<18} still has placeholder value")
        warnings.append(key)
    elif key == "SERPER_API_KEY" and len(value) < 10:
        print(f"  ⚠️   {key:<18} looks too short — double-check")
        warnings.append(key)
    elif key == "GMAIL_APP_PASS" and len(value) < 16:
        print(f"  ⚠️   {key:<18} App Password should be 16 chars")
        warnings.append(key)
    else:
        display = val_str[:35] + "…" if len(val_str) > 35 else val_str
        print(f"  ✅  {key:<18} {display}")

print("─"*52)

# Extra checks
print("\n  📋  Internship roles configured:")
for role in cfg.INTERNSHIP_ROLES:
    print(f"       • {role}")

print(f"\n  📍  Preferred locations: {', '.join(cfg.PREFERRED_LOCATIONS)}")
print(f"  💰  Min stipend filter:  ₹{cfg.MIN_STIPEND:,}/month")
print(f"  📂  DB path:             {cfg.DB_PATH}")
print(f"  📝  Log path:            {cfg.LOG_PATH}")

print("\n" + "─"*52)
if all_ok and not warnings:
    print("  🎉  All checks passed! You're ready for Day 2.")
elif warnings:
    print(f"  ⚠️   {len(warnings)} key(s) still need real values:")
    for w in warnings:
        print(f"       → {w}  (edit your .env file)")
    print("\n  Once filled, re-run:  python verify_config.py")
else:
    print("  ❌  Fix the missing keys above, then re-run.")
print("─"*52 + "\n")
