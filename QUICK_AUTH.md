# Authentication Quick Start

## TL;DR - Just Run This:

```powershell
python test_auth_flow.py
```

This will automatically:
- ✅ Register a user
- ✅ Login
- ✅ Test authenticated API call
- ✅ Show you the access token

---

## Or Use These Commands:

### Register
```powershell
$body = '{"email":"test@example.com","username":"test","password":"MyVeryUniqueP@ssw0rd2026!","tenant_id":"00000000-0000-0000-0000-000000000001"}'
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/register" -Method Post -Body $body -ContentType "application/json"
```

### Login
```powershell
$body = '{"email":"test@example.com","password":"MyVeryUniqueP@ssw0rd2026!"}'
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method Post -Body $body -ContentType "application/json"
$token = $response.access_token
Write-Host "Token: $token"
```

### Use Token
```powershell
$headers = @{"Authorization"="Bearer $token"; "X-Tenant-ID"="00000000-0000-0000-0000-000000000001"}
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/tasks" -Headers $headers
```

---

## ⚠️ Important

**DO NOT USE**: `SecurePass123!@#` - This password is compromised!
**USE INSTEAD**: `MyVeryUniqueP@ssw0rd2026!` or any unique password

---

## Files to Help You

- `test_auth_flow.py` - Automated test (just run it!)
- `test_auth.http` - HTTP requests (click play buttons in PyCharm)
- `AUTHENTICATION_GUIDE.md` - Complete documentation
- `PASSWORD_ISSUE_RESOLUTION.md` - Explains the password issue

---

## Interactive API Docs (Easiest Way!)

1. Open: http://localhost:8000/docs
2. Find POST `/api/v1/auth/login`
3. Click "Try it out"
4. Enter email and password
5. Click "Execute"
6. Copy the access_token
7. Click "Authorize" button at top
8. Paste token and authorize
9. Now test any endpoint!

