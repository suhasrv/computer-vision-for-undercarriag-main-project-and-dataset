import httpx

email = 'admincreate-00a6ed94ff454721b4200d1c96345138@example.com'
password = 'Test1234!'
url = 'https://awhmnadlztcalkdgzclb.supabase.co/auth/v1/token?grant_type=password'
headers = {'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF3aG1uYWRsenRjYWxrZGd6Y2xiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU4Mjg2MjMsImV4cCI6MjA5MTQwNDYyM30.qIV-fP4HSUbUZLcKNQUADuPfvpW0M6eWHBGvy1wlv9I', 'Content-Type': 'application/json'}

with httpx.Client() as c:
    r = c.post(url, json={'email': email, 'password': password}, headers=headers, timeout=10.0)
    print('STATUS', r.status_code)
    print(r.text)
