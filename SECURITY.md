# Security Guidelines - JobQuick AI

## Critical Security Measures

### 1. Secrets Management

**Never commit these to version control:**
- JWT_SECRET
- ADMIN_PASSWORD
- EMERGENT_LLM_KEY
- Database credentials
- API keys

**Best practices:**
```bash
# Generate strong JWT secret
openssl rand -hex 32

# Use environment variables
export JWT_SECRET="your-generated-secret"

# Or use .env file (add to .gitignore)
echo ".env" >> .gitignore
```

### 2. Password Security

**Requirements enforced:**
- Minimum 8 characters
- Must contain uppercase letters
- Must contain lowercase letters
- Must contain numbers

**Hashing:**
- bcrypt with auto-generated salt
- No plain-text passwords stored

```python
# Passwords are hashed before storage
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
```

### 3. Authentication & Authorization

**JWT Tokens:**
- 7-day expiration
- HS256 algorithm
- Includes user ID in payload

**Role-based access:**
- Admin: Full platform access
- Employer: Job management, candidate screening
- Job Seeker: Profile, applications, job search

**Protected endpoints:**
All `/api/*` endpoints (except auth) require valid JWT token.

### 4. File Upload Security

**Restrictions:**
- Max file size: 5MB (configurable)
- Allowed formats: PDF, DOCX, TXT only
- Virus scanning: Recommended (not implemented)

```python
# Validation in place
if len(file_bytes) > MAX_SIZE:
    raise HTTPException(400, "File too large")

if file_ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(400, "Invalid file type")
```

### 5. Input Validation

**Email validation:**
- Pydantic EmailStr type
- Format validation
- Uniqueness check

**SQL Injection prevention:**
- MongoDB query parameterization
- No string concatenation in queries

**XSS prevention:**
- React auto-escapes output
- No `dangerouslySetInnerHTML` used

### 6. CORS Configuration

**Development:**
```python
CORS_ORIGINS="*"  # Allow all (dev only)
```

**Production:**
```python
CORS_ORIGINS="https://jobquick.ai,https://www.jobquick.ai"
```

### 7. Rate Limiting

**Recommended (not implemented):**
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/auth/login")
@limiter.limit("5/minute")
async def login(...):
    ...
```

### 8. Database Security

**MongoDB best practices:**
1. Enable authentication
   ```javascript
   use admin
   db.createUser({
     user: "jobquick",
     pwd: "strong-password",
     roles: [{role: "readWrite", db: "jobquick_production"}]
   })
   ```

2. Bind to localhost or private network
   ```yaml
   net:
     bindIp: 127.0.0.1
   ```

3. Enable audit logging
4. Regular backups
5. Encryption at rest (MongoDB Enterprise)

### 9. API Security Headers

**Recommended headers:**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["jobquick.ai", "*.jobquick.ai"]
)
```

### 10. Logging & Monitoring

**Do log:**
- Authentication attempts
- Failed login attempts
- Admin actions
- API errors
- File uploads

**Don't log:**
- Passwords
- JWT tokens
- API keys
- Sensitive user data

## Security Checklist

### Pre-Launch
- [ ] All secrets in environment variables
- [ ] JWT_SECRET is strong (32+ chars)
- [ ] Admin password changed from default
- [ ] CORS configured for production domain
- [ ] Database authentication enabled
- [ ] HTTPS enabled (SSL certificate)
- [ ] File upload limits configured
- [ ] Password requirements enforced

### Post-Launch
- [ ] Monitor failed login attempts
- [ ] Regular security audits
- [ ] Keep dependencies updated
- [ ] Monitor for suspicious activity
- [ ] Regular backups verified
- [ ] Incident response plan in place

## Vulnerability Reporting

If you discover a security vulnerability:
1. Do NOT create public GitHub issue
2. Email: security@jobquick.ai
3. Include: description, impact, reproduction steps
4. We will respond within 48 hours

## Compliance

### GDPR Considerations
- User data minimization
- Right to deletion (implement user account deletion)
- Data export capability
- Privacy policy required
- Cookie consent required

### Data Retention
- User accounts: Until deletion requested
- Resumes: Linked to user account
- Applications: Keep for legal requirements
- Logs: 90 days recommended

## Security Updates

**Regular tasks:**
```bash
# Update Python dependencies
pip install --upgrade -r requirements.txt

# Update Node dependencies
yarn upgrade

# Check for vulnerabilities
pip-audit
yarn audit
```

## Emergency Response

### If credentials are compromised:
1. Rotate JWT_SECRET immediately
2. Invalidate all user sessions
3. Force password resets
4. Review access logs
5. Notify affected users

### If data breach occurs:
1. Isolate affected systems
2. Preserve evidence
3. Assess scope
4. Notify authorities (if required)
5. Notify affected users
6. Conduct post-mortem
