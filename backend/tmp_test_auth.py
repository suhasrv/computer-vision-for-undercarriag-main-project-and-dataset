import httpx
import uuid

email = f"copilot-py-{uuid.uuid4().hex}@example.com"
password = "Test1234!"
payload = {"email": email, "password": password}

print("TEST_EMAIL:", email)

with httpx.Client() as c:
    try:
        r = c.post("http://127.0.0.1:8000/v1/register", json=payload, timeout=10.0)
        print("REGISTER", r.status_code)
        print(r.text)
    except Exception as e:
        print("REGISTER_ERROR", e)

    try:
        r2 = c.post("http://127.0.0.1:8000/v1/login", json=payload, timeout=10.0)
        print("LOGIN", r2.status_code)
        print(r2.text)
    except Exception as e:
        print("LOGIN_ERROR", e)
