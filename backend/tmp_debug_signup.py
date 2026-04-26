import os
import uuid
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

def try_signup(email, password):
    url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    payload = {"email": email, "password": password}
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    print("SIGNUP ->", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)

def try_token(email, password):
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    payload = {"email": email, "password": password}
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    print("TOKEN ->", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)

if __name__ == "__main__":
    password = "Test1234!"
    # Try multiple domains to detect domain validation issues
    domains = ["example.com", "gmail.com", "test.org"]
    for d in domains:
        email = f"copilot-debug-{uuid.uuid4().hex}@{d}"
        print("\nDEBUG_EMAIL:", email)
        try_signup(email, password)
        try_token(email, password)
