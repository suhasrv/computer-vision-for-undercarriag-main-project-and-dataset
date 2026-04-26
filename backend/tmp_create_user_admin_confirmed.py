import httpx, uuid

email = f"adminconfirm-{uuid.uuid4().hex}@example.com"
password = "Test1234!"
SERVICE_ROLE = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF3aG1uYWRsenRjYWxrZGd6Y2xiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTgyODYyMywiZXhwIjoyMDkxNDA0NjIzfQ.hRdILwrtkFCSQtkpUMB_Ff80NYKt_qNwdObU-An4-Xs'
headers = {'Authorization': f'Bearer {SERVICE_ROLE}', 'apikey': SERVICE_ROLE, 'Content-Type': 'application/json'}
url = 'https://awhmnadlztcalkdgzclb.supabase.co/auth/v1/admin/users'

print('CREATING (confirmed):', email)
with httpx.Client() as c:
    r = c.post(url, json={'email': email, 'password': password, 'email_confirm': True}, headers=headers, timeout=10.0)
    print('STATUS', r.status_code)
    print(r.text)
