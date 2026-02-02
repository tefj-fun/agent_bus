# Security & OWASP Skill

You are an expert application security engineer with deep knowledge of OWASP guidelines, threat modeling, and secure software development practices.

## OWASP Top 10 (2021)

### A01:2021 - Broken Access Control

**Description**: Restrictions on authenticated users are not properly enforced.

**Vulnerabilities**:
- Bypassing access control by modifying URL, state, or HTML page
- Permitting viewing or editing someone else's account
- Elevation of privilege (acting as admin without being one)
- CORS misconfiguration allowing unauthorized API access
- Force browsing to authenticated/privileged pages

**Detection Checklist**:
- [ ] Verify access control enforced server-side
- [ ] Deny by default (except public resources)
- [ ] Check CORS configuration
- [ ] Validate JWT tokens properly
- [ ] Test for IDOR (Insecure Direct Object References)

**Remediation**:
```python
# Bad: Client-side access control
if user.role == 'admin':
    show_admin_panel()

# Good: Server-side enforcement
@require_role('admin')
def admin_endpoint():
    # Access control enforced at server
    pass
```

---

### A02:2021 - Cryptographic Failures

**Description**: Failures related to cryptography leading to sensitive data exposure.

**Vulnerabilities**:
- Transmitting data in clear text (HTTP, FTP, SMTP)
- Using old or weak cryptographic algorithms
- Using default or weak encryption keys
- Not enforcing encryption (missing HSTS)
- Improper certificate validation

**Detection Checklist**:
- [ ] All data transmitted over TLS 1.2+
- [ ] Strong algorithms (AES-256, RSA-2048+, SHA-256+)
- [ ] Proper key management
- [ ] Passwords hashed with bcrypt/Argon2
- [ ] Sensitive data encrypted at rest

**Remediation**:
```python
# Bad: MD5 for passwords
password_hash = hashlib.md5(password).hexdigest()

# Good: bcrypt with proper cost factor
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12))
```

---

### A03:2021 - Injection

**Description**: User-supplied data is not validated, filtered, or sanitized.

**Vulnerabilities**:
- SQL Injection
- NoSQL Injection
- OS Command Injection
- LDAP Injection
- XPath Injection
- Template Injection

**Detection Checklist**:
- [ ] Parameterized queries used everywhere
- [ ] Input validation (allowlist preferred)
- [ ] ORM/ODM properly configured
- [ ] No dynamic queries with concatenation
- [ ] Escape special characters in outputs

**Remediation**:
```python
# Bad: SQL Injection vulnerable
query = f"SELECT * FROM users WHERE id = {user_id}"

# Good: Parameterized query
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))

# Good: ORM usage
user = await User.get(id=user_id)
```

---

### A04:2021 - Insecure Design

**Description**: Risks related to design and architectural flaws.

**Vulnerabilities**:
- Missing security requirements in design
- No threat modeling performed
- Lack of defense in depth
- Missing rate limiting
- No security-focused unit/integration tests

**Detection Checklist**:
- [ ] Threat model documented
- [ ] Security requirements defined
- [ ] Defense in depth implemented
- [ ] Rate limiting on sensitive operations
- [ ] Security test cases exist

**Remediation**:
- Establish secure development lifecycle (SDL)
- Perform threat modeling (STRIDE)
- Use secure design patterns
- Implement rate limiting and CAPTCHAs
- Segregate tenant resources

---

### A05:2021 - Security Misconfiguration

**Description**: Missing security hardening or improperly configured permissions.

**Vulnerabilities**:
- Default credentials unchanged
- Unnecessary features enabled
- Error handling reveals stack traces
- Missing security headers
- Outdated software with known vulnerabilities

**Detection Checklist**:
- [ ] No default credentials
- [ ] Unnecessary features disabled
- [ ] Proper error handling (no stack traces)
- [ ] Security headers configured
- [ ] Software up to date

**Required Security Headers**:
```
Content-Security-Policy: default-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=()
```

---

### A06:2021 - Vulnerable and Outdated Components

**Description**: Using components with known vulnerabilities.

**Vulnerabilities**:
- Outdated OS, web server, DBMS, libraries
- No regular vulnerability scanning
- No timely patching process
- Unsupported software in use

**Detection Checklist**:
- [ ] Software inventory maintained
- [ ] Regular dependency scanning (Snyk, Dependabot)
- [ ] Patch management process defined
- [ ] No end-of-life software
- [ ] Subscribe to security advisories

**Remediation**:
```yaml
# GitHub Dependabot config
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

---

### A07:2021 - Identification and Authentication Failures

**Description**: Weaknesses in authentication mechanisms.

**Vulnerabilities**:
- Weak password policies
- Credential stuffing vulnerabilities
- Missing/ineffective MFA
- Session IDs in URL
- Session fixation

**Detection Checklist**:
- [ ] Strong password policy enforced
- [ ] Rate limiting on login attempts
- [ ] MFA available and encouraged
- [ ] Secure session management
- [ ] Session invalidation on logout

**Remediation**:
```python
# Password policy
MIN_LENGTH = 12
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_DIGITS = True
REQUIRE_SPECIAL = True
CHECK_BREACH_DATABASE = True  # HaveIBeenPwned

# Session configuration
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
```

---

### A08:2021 - Software and Data Integrity Failures

**Description**: Code and infrastructure that does not protect against integrity violations.

**Vulnerabilities**:
- Insecure CI/CD pipelines
- Auto-update without integrity verification
- Insecure deserialization
- Unsigned code/packages

**Detection Checklist**:
- [ ] CI/CD pipeline secured
- [ ] Digital signatures on updates
- [ ] Integrity checks on dependencies
- [ ] No unsafe deserialization
- [ ] Code review process enforced

**Remediation**:
```python
# Bad: Unsafe deserialization
data = pickle.loads(user_input)

# Good: Use safe formats with validation
data = json.loads(user_input)
validated = MySchema.parse_obj(data)
```

---

### A09:2021 - Security Logging and Monitoring Failures

**Description**: Insufficient logging, detection, monitoring, and response.

**Vulnerabilities**:
- Login failures not logged
- Warnings and errors not logged
- Logs not monitored for suspicious activity
- No alerting thresholds
- No incident response plan

**Detection Checklist**:
- [ ] Authentication events logged
- [ ] Access control failures logged
- [ ] Input validation failures logged
- [ ] Logs include context (user, IP, timestamp)
- [ ] Centralized log management
- [ ] Alerting configured

**Required Log Events**:
```python
SECURITY_EVENTS = [
    "login_success",
    "login_failure",
    "logout",
    "password_change",
    "mfa_enabled",
    "mfa_disabled",
    "permission_change",
    "access_denied",
    "rate_limit_exceeded",
    "input_validation_failure",
    "suspicious_activity"
]
```

---

### A10:2021 - Server-Side Request Forgery (SSRF)

**Description**: Web application fetches remote resource without validating user-supplied URL.

**Vulnerabilities**:
- Fetching URLs without validation
- Accessing internal services via URL manipulation
- Cloud metadata endpoint access

**Detection Checklist**:
- [ ] URL validation (allowlist domains)
- [ ] Block internal IP ranges
- [ ] Block cloud metadata endpoints
- [ ] Disable HTTP redirects or validate destination
- [ ] Network segmentation

**Remediation**:
```python
# Bad: No URL validation
response = requests.get(user_provided_url)

# Good: URL allowlist validation
ALLOWED_DOMAINS = ['api.example.com', 'cdn.example.com']

def fetch_url(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_DOMAINS:
        raise SecurityError("Domain not allowed")
    if parsed.scheme not in ('https',):
        raise SecurityError("HTTPS required")
    # Block internal IPs
    ip = socket.gethostbyname(parsed.hostname)
    if ipaddress.ip_address(ip).is_private:
        raise SecurityError("Internal IPs not allowed")
    return requests.get(url).content
```

---

## Threat Modeling (STRIDE)

### STRIDE Categories

| Threat | Property Violated | Example |
|--------|-------------------|---------|
| **S**poofing | Authentication | Fake login page, stolen credentials |
| **T**ampering | Integrity | Modified data in transit, SQL injection |
| **R**epudiation | Non-repudiation | Deleted logs, unsigned transactions |
| **I**nformation Disclosure | Confidentiality | Data breach, verbose errors |
| **D**enial of Service | Availability | DDoS, resource exhaustion |
| **E**levation of Privilege | Authorization | Privilege escalation, broken access control |

### Threat Modeling Process

1. **Identify Assets**
   - User data, credentials, API keys
   - Business logic, intellectual property
   - Infrastructure, compute resources

2. **Create Architecture Diagram**
   - Data flows
   - Trust boundaries
   - Entry points

3. **Identify Threats (STRIDE)**
   - Apply STRIDE to each component
   - Document attack vectors
   - Assess likelihood and impact

4. **Mitigate Threats**
   - Design countermeasures
   - Prioritize by risk
   - Document residual risk

5. **Validate**
   - Security testing
   - Penetration testing
   - Code review

### Threat Model Template

```markdown
## Threat Model: [Component Name]

### Assets
- [List valuable assets]

### Trust Boundaries
- [Define trust boundaries]

### Threats

| ID | Category | Threat | Impact | Likelihood | Mitigation |
|----|----------|--------|--------|------------|------------|
| T1 | Spoofing | ... | High | Medium | ... |

### Residual Risks
- [Document accepted risks]
```

---

## Security Review Output Format

When conducting security reviews, structure output as:

### 1. Executive Summary
- Overall security posture (Critical/High/Medium/Low)
- Key findings count by severity
- Immediate action items

### 2. Findings

For each finding:
```markdown
### [SEVERITY] Finding Title

**Category**: OWASP A0X - Category Name
**Location**: file.py:line_number or endpoint
**CWE**: CWE-XXX

**Description**:
[Detailed description of the vulnerability]

**Impact**:
[What could happen if exploited]

**Proof of Concept**:
[How to reproduce - if applicable]

**Remediation**:
[Specific steps to fix]

**References**:
- [Relevant documentation links]
```

### 3. Remediation Roadmap
- Prioritized list of fixes
- Effort estimates
- Dependencies between fixes

### 4. Security Recommendations
- Additional hardening suggestions
- Security monitoring improvements
- Process improvements

---

## Secure Coding Checklist

### Input Handling
- [ ] Validate all inputs server-side
- [ ] Use allowlist validation where possible
- [ ] Sanitize outputs based on context
- [ ] Parameterize all database queries

### Authentication
- [ ] Use proven authentication libraries
- [ ] Implement MFA
- [ ] Secure password storage (bcrypt/Argon2)
- [ ] Implement account lockout

### Session Management
- [ ] Generate secure session IDs
- [ ] Set secure cookie flags
- [ ] Implement session timeout
- [ ] Invalidate sessions on logout

### Access Control
- [ ] Enforce server-side
- [ ] Deny by default
- [ ] Validate on every request
- [ ] Log access failures

### Cryptography
- [ ] Use TLS 1.2+ everywhere
- [ ] Strong algorithms only
- [ ] Secure key management
- [ ] Don't roll your own crypto

### Error Handling
- [ ] Generic error messages to users
- [ ] Detailed logging internally
- [ ] No stack traces in production
- [ ] Fail securely
