import httpx

email = 'admincreate-00a6ed94ff454721b4200d1c96345138@example.com'
password = 'Test1234!'

print('LOGIN TEST EMAIL:', email)

with httpx.Client() as c:
    r = c.post('http://127.0.0.1:8000/v1/login', json={'email': email, 'password': password}, timeout=10.0)
    print('STATUS', r.status_code)
    print(r.text)
