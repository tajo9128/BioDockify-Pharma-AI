# BioDockify AI - Operational Rules for AI Agent

## 🌍 International Project Standards

This is an **international pharmaceutical research platform**. All operations must adhere to global standards.

### 1. Language & Region Awareness

**MANDATORY BEHAVIORS:**
- Always detect or ask for user's language preference
- Use ISO 639-1 language codes (en, zh, es, fr, de, ja, ko, ar, pt, ru)
- Use ISO 3166-1 alpha-2 region codes (US, CN, EU, JP, etc.)
- Support RTL (Right-to-Left) languages (Arabic, Hebrew, Farsi)
- Never assume English is the primary language
- Ask clarifying questions if language/region is unclear

**FORBIDDEN BEHAVIORS:**
- ❌ Hardcoding text in any single language
- ❌ Assuming cultural norms without verification
- ❌ Using colloquialisms that don't translate
- ❌ Ignoring timezone differences

### 2. Data Compliance (GDPR/CCPA/ISO)

**MANDATORY BEHAVIORS:**
- Check user's region before processing personal data
- Enable GDPR mode for EU users (explicit consent required)
- Enable CCPA mode for California users (data deletion rights)
- Follow ISO 27001 information security standards
- Follow ISO 9001 quality management standards
- Follow Good Laboratory Practice (GLP) guidelines
- Follow Good Clinical Practice (GCP) guidelines for medical research
- Always obtain consent before processing user data
- Provide data export/deletion capabilities when requested

**FORBIDDEN BEHAVIORS:**
- ❌ Processing personal data without consent
- ❌ Storing data in non-compliant regions
- ❌ Ignoring data deletion requests
- ❌ Processing medical data without proper safeguards

### 3. Cultural Sensitivity

**MANDATORY BEHAVIORS:**
- Respect local holidays and working hours
- Avoid scheduling tasks during non-business hours in user's timezone
- Use culturally appropriate date/time formats (ISO 8601 recommended)
- Display currencies in local format when applicable
- Be aware of cultural differences in communication styles

**FORBIDDEN BEHAVIORS:**
- ❌ Scheduling important tasks during religious holidays
- ❌ Using culturally insensitive imagery or language
- ❌ Ignoring regional business customs

### 4. Security & Privacy (CRITICAL)

**MANDATORY BEHAVIORS:**
- NEVER hardcode API keys, passwords, or secrets in repository files
- ALWAYS use environment variables or secure vaults for secrets
- Verify all API keys are empty/placeholder before committing
- Run security scans (bandit, pylint) before deploying
- Check .dockerignore includes all secret files
- Never ship credentials in Docker images
- Use defusedxml for XML parsing (not lxml/ElementTree)
- Add timeouts to all network requests
- Validate and sanitize all user inputs
- Use parameterized queries for database operations
- Never use eval() with user input (use ast.literal_eval instead)

**FORBIDDEN BEHAVIORS:**
- ❌ Hardcoding API keys in config.yaml, .env, or any files
- ❌ Committing secrets to git
- ❌ Using eval() with untrusted input
- ❌ Parsing XML without defusedxml
- ❌ Making network requests without timeouts
- ❌ Shipping credentials in Docker images

### 5. Code Quality & Standards

**MANDATORY BEHAVIORS:**
- Follow PEP 8 for Python code
- Use TypeScript strict mode for frontend code
- Write unit tests for all critical functions
- Add docstrings to all functions and classes
- Use type hints throughout Python code
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Document all breaking changes
- Maintain backward compatibility when possible

**FORBIDDEN BEHAVIORS:**
- ❌ Pushing code without tests
- ❌ Breaking backward compatibility without proper version bump
- ❌ Ignoring linting warnings
- ❌ Leaving commented-out code in commits

### 6. LLM API Configuration

**MANDATORY BEHAVIORS:**
- NEVER pre-configure LLM providers in release builds
- Allow users to configure their own API keys via Settings UI
- Support environment variables for automated deployments
- Document all supported LLM providers clearly
- Test connection before using any LLM provider
- Provide clear error messages when authentication fails

**FORBIDDEN BEHAVIORS:**
- ❌ Hardcoding API keys for any LLM provider
- ❌ Shipping pre-configured API keys in Docker images
- ❌ Assuming a specific LLM provider will be used
- ❌ Releasing with placeholder keys that look real

### 7. Pharmaceutical Research Specifics

**MANDATORY BEHAVIORS:**
- Follow FDA/EMA guidelines for medical software
- Validate all scientific calculations
- Provide source citations for research claims
- Use peer-reviewed literature when possible
- Maintain data integrity for research results
- Follow reproducibility standards (include all parameters)

**FORBIDDEN BEHAVIORS:**
- ❌ Making medical claims without verification
- ❌ Using unverified research sources
- ❌ Ignoring data provenance
- ❌ Modifying research data without audit trail

### 8. Error Handling & Communication

**MANDATORY BEHAVIORS:**
- Provide error messages in user's preferred language
- Include actionable troubleshooting steps
- Log errors with appropriate severity levels
- Never expose sensitive data in error messages
- Graceful degradation when external services fail

**FORBIDDEN BEHAVIORS:**
- ❌ Showing stack traces to end users
- ❌ Exposing API keys in error messages
- ❌ Using generic error messages that don't help

### 9. Deployment & Release

**MANDATORY BEHAVIORS:**
- Verify no secrets in committed files before release
- Test Docker image build before pushing to registry
- Update version.txt in all release commits
- Provide clear release notes with: features, fixes, breaking changes
- Tag releases with semantic version numbers
- Verify environment variables are properly documented

**FORBIDDEN BEHAVIORS:**
- ❌ Pushing release without testing Docker build
- ❌ Skipping version update in release
- ❌ Releasing with misleading release notes
- ❌ Pushing to Docker registry without verification

### 10. Verification Checklist (Before Each Commit)

**Run this checklist before any commit to main branch:**

```
[ ] No API keys, passwords, or secrets in files
[ ] All hardcoded keys are empty strings or placeholders
[ ] .dockerignore includes .env, secrets.env, *.key
[ ] No eval() with user input (use ast.literal_eval)
[ ] All XML parsing uses defusedxml
[ ] All network requests have timeouts
[ ] Tests pass for modified code
[ ] Security scans pass (bandit, pylint)
[ ] Documentation updated for new features
[ ] Release notes are accurate and not misleading
[ ] Version number updated if this is a release
```

## 🚨 EMERGENCY PROTOCOLS

### If You Discover a Security Issue:
1. STOP all operations immediately
2. Do NOT commit or push changes
3. Report the issue clearly to the user
4. Provide remediation steps
5. Wait for user approval before proceeding

### If You Make a Mistake:
1. Acknowledge it immediately and clearly
2. Explain what went wrong
3. Provide the fix
4. Explain how to prevent it in the future
5. Commit the fix as a separate patch release if needed

## 📋 Summary of Critical Rules

1. **NEVER hardcode API keys or secrets** in any committed file
2. **ALWAYS respect user's language/region preferences**
3. **ALWAYS obtain consent before processing personal data**
4. **NEVER assume English or any single language**
5. **ALWAYS use ISO standards** (639-1 for language, 3166-1 for country, 8601 for datetime)
6. **NEVER use eval() with user input** - use ast.literal_eval
7. **ALWAYS use defusedxml for XML parsing**
8. **NEVER ship credentials in Docker images**
9. **ALWAYS run security scans** before deployment
10. **NEVER make misleading claims in release notes**

---

**Last Updated:** 2026-02-13
**Version:** 1.0

Follow these rules strictly. Violation may result in security vulnerabilities, legal compliance issues, or poor user experience.
