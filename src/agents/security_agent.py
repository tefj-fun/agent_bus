"""Security Agent - Conducts security review and vulnerability assessment."""

import json
from typing import Any, Dict

from .base import BaseAgent, AgentTask, AgentResult


class SecurityAgent(BaseAgent):
    """Agent specialized in security review and vulnerability assessment."""

    def get_agent_id(self) -> str:
        """Return unique agent identifier."""
        return "security_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        """Define agent capabilities."""
        return {
            "can_conduct_security_audit": True,
            "can_identify_vulnerabilities": True,
            "can_recommend_mitigations": True,
            "can_assess_compliance": True,
            "output_formats": ["json", "markdown"],
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Generate security audit and vulnerability assessment.

        Args:
            task: Task definition

        Returns:
            Agent result with security artifact
        """
        try:
            await self.log_event("info", "Starting security review")

            development_content = task.input_data.get("development") or ""
            architecture_content = task.input_data.get("architecture") or ""
            qa_content = task.input_data.get("qa") or ""
            prd_content = task.input_data.get("prd") or ""

            if not development_content.strip():
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=False,
                    output={},
                    artifacts=[],
                    error="Missing development content for security review",
                )

            # Build comprehensive system prompt
            system_prompt = self._build_security_system_prompt()

            # Generate security audit (real LLM or mock)
            user_prompt = self._build_security_user_prompt(
                development_content, architecture_content, qa_content, prd_content
            )

            from ..config import settings

            if settings.llm_mode == "mock":
                security_payload = {
                    "security_audit": {
                        "audit_date": "2026-02-01",
                        "audit_scope": "Full application security review",
                        "security_level": "medium-risk",
                        "overall_rating": "B+",
                        "summary": "Application demonstrates good security practices with some areas requiring attention",
                    },
                    "vulnerabilities": [
                        {
                            "vulnerability_id": "SEC-001",
                            "severity": "high",
                            "category": "authentication",
                            "title": "Missing rate limiting on authentication endpoints",
                            "description": "Authentication endpoints lack rate limiting, making them vulnerable to brute force attacks",
                            "affected_components": ["API authentication", "Login endpoint"],
                            "cwe_id": "CWE-307",
                            "cvss_score": 7.5,
                            "exploit_likelihood": "high",
                            "impact": "Account compromise through credential stuffing or brute force",
                            "recommendation": "Implement rate limiting with exponential backoff on all authentication endpoints",
                            "mitigation_priority": "high",
                            "estimated_effort": "2-4 hours",
                        },
                        {
                            "vulnerability_id": "SEC-002",
                            "severity": "high",
                            "category": "injection",
                            "title": "Potential SQL injection in user query parameter",
                            "description": "User input not properly sanitized before database queries",
                            "affected_components": ["Database layer", "User search API"],
                            "cwe_id": "CWE-89",
                            "cvss_score": 8.2,
                            "exploit_likelihood": "medium",
                            "impact": "Unauthorized data access, data manipulation, potential data exfiltration",
                            "recommendation": "Use parameterized queries or ORM with proper input validation",
                            "mitigation_priority": "critical",
                            "estimated_effort": "4-8 hours",
                        },
                        {
                            "vulnerability_id": "SEC-003",
                            "severity": "medium",
                            "category": "access_control",
                            "title": "Insufficient authorization checks on API endpoints",
                            "description": "Some endpoints do not verify user permissions before allowing operations",
                            "affected_components": ["API middleware", "Resource access endpoints"],
                            "cwe_id": "CWE-285",
                            "cvss_score": 6.5,
                            "exploit_likelihood": "medium",
                            "impact": "Unauthorized access to resources, privilege escalation",
                            "recommendation": "Implement comprehensive RBAC with middleware enforcement on all endpoints",
                            "mitigation_priority": "high",
                            "estimated_effort": "8-16 hours",
                        },
                        {
                            "vulnerability_id": "SEC-004",
                            "severity": "medium",
                            "category": "data_exposure",
                            "title": "Sensitive data logged in application logs",
                            "description": "PII and credentials appear in log files without redaction",
                            "affected_components": ["Logging middleware", "Error handlers"],
                            "cwe_id": "CWE-532",
                            "cvss_score": 5.3,
                            "exploit_likelihood": "low",
                            "impact": "Exposure of sensitive data if logs are compromised",
                            "recommendation": "Implement log sanitization to redact PII, passwords, and tokens",
                            "mitigation_priority": "medium",
                            "estimated_effort": "2-4 hours",
                        },
                        {
                            "vulnerability_id": "SEC-005",
                            "severity": "low",
                            "category": "cryptography",
                            "title": "Weak session token generation",
                            "description": "Session tokens use insufficient entropy",
                            "affected_components": ["Session management"],
                            "cwe_id": "CWE-330",
                            "cvss_score": 4.3,
                            "exploit_likelihood": "low",
                            "impact": "Session hijacking through token prediction",
                            "recommendation": "Use cryptographically secure random token generation (e.g., secrets.token_urlsafe)",
                            "mitigation_priority": "medium",
                            "estimated_effort": "1-2 hours",
                        },
                        {
                            "vulnerability_id": "SEC-006",
                            "severity": "low",
                            "category": "configuration",
                            "title": "Missing security headers",
                            "description": "Response lacks security headers (CSP, X-Frame-Options, HSTS)",
                            "affected_components": ["HTTP middleware"],
                            "cwe_id": "CWE-693",
                            "cvss_score": 3.7,
                            "exploit_likelihood": "low",
                            "impact": "Increased attack surface for XSS and clickjacking",
                            "recommendation": "Add comprehensive security headers via middleware",
                            "mitigation_priority": "low",
                            "estimated_effort": "1-2 hours",
                        },
                    ],
                    "security_recommendations": [
                        {
                            "category": "authentication",
                            "priority": "high",
                            "recommendation": "Implement multi-factor authentication (MFA)",
                            "rationale": "MFA significantly reduces account compromise risk",
                            "implementation_guidance": "Support TOTP-based MFA with backup codes",
                        },
                        {
                            "category": "encryption",
                            "priority": "high",
                            "recommendation": "Encrypt sensitive data at rest",
                            "rationale": "Protection against database compromise",
                            "implementation_guidance": "Use AES-256 encryption for PII and credentials",
                        },
                        {
                            "category": "dependencies",
                            "priority": "high",
                            "recommendation": "Implement automated dependency scanning",
                            "rationale": "Early detection of vulnerable dependencies",
                            "implementation_guidance": "Integrate Dependabot or Snyk in CI/CD pipeline",
                        },
                        {
                            "category": "monitoring",
                            "priority": "medium",
                            "recommendation": "Establish security monitoring and alerting",
                            "rationale": "Early detection of security incidents",
                            "implementation_guidance": "Log authentication failures, suspicious patterns, and anomalies",
                        },
                        {
                            "category": "access_control",
                            "priority": "medium",
                            "recommendation": "Implement principle of least privilege",
                            "rationale": "Minimize impact of compromised accounts",
                            "implementation_guidance": "Review and restrict default permissions",
                        },
                        {
                            "category": "incident_response",
                            "priority": "medium",
                            "recommendation": "Create incident response plan",
                            "rationale": "Structured response to security incidents",
                            "implementation_guidance": "Document procedures for breach detection and response",
                        },
                    ],
                    "compliance_assessment": {
                        "standards_evaluated": ["OWASP Top 10", "CWE Top 25", "GDPR", "SOC 2"],
                        "owasp_top_10_coverage": {
                            "A01_broken_access_control": "partial",
                            "A02_cryptographic_failures": "needs_attention",
                            "A03_injection": "needs_attention",
                            "A04_insecure_design": "good",
                            "A05_security_misconfiguration": "needs_attention",
                            "A06_vulnerable_components": "needs_attention",
                            "A07_authentication_failures": "needs_attention",
                            "A08_software_data_integrity": "good",
                            "A09_security_logging_monitoring": "partial",
                            "A10_server_side_request_forgery": "good",
                        },
                        "gdpr_compliance": {
                            "data_encryption": "partial",
                            "access_controls": "partial",
                            "audit_logging": "needs_improvement",
                            "data_retention": "not_assessed",
                            "breach_notification": "not_implemented",
                        },
                        "recommendations": [
                            "Address high and critical vulnerabilities before production deployment",
                            "Implement comprehensive audit logging for compliance",
                            "Conduct penetration testing before go-live",
                            "Establish data retention and deletion policies",
                        ],
                    },
                    "security_best_practices": {
                        "implemented": [
                            "Password hashing with bcrypt/argon2",
                            "HTTPS enforcement",
                            "Input validation on user inputs",
                            "Secure password requirements",
                            "CORS configuration",
                        ],
                        "missing": [
                            "Rate limiting on API endpoints",
                            "Comprehensive security headers",
                            "Multi-factor authentication",
                            "Automated security scanning in CI/CD",
                            "Data encryption at rest",
                            "Security audit logging",
                            "Web Application Firewall (WAF)",
                        ],
                    },
                    "penetration_testing": {
                        "recommended_scope": [
                            "Authentication and authorization bypass attempts",
                            "SQL injection and XSS testing",
                            "API security testing",
                            "Session management testing",
                            "Business logic flaws",
                        ],
                        "timing": "Before production deployment",
                        "frequency": "Annually or after major changes",
                    },
                    "security_metrics": {
                        "vulnerabilities_by_severity": {
                            "critical": 0,
                            "high": 2,
                            "medium": 3,
                            "low": 2,
                            "info": 0,
                        },
                        "estimated_remediation_effort": "22-40 hours",
                        "security_debt_score": 6.2,
                        "attack_surface_score": 7.1,
                    },
                    "next_steps": [
                        "1. Address critical and high-severity vulnerabilities immediately",
                        "2. Implement rate limiting and parameterized queries as priority",
                        "3. Add comprehensive authorization middleware",
                        "4. Integrate automated security scanning in CI/CD",
                        "5. Conduct penetration testing before production release",
                        "6. Establish ongoing security monitoring and incident response procedures",
                    ],
                }
                security_content = json.dumps(security_payload, indent=2)
            else:
                response_text = await self.query_llm(
                    prompt=user_prompt, system=system_prompt, thinking_budget=2048, max_tokens=8192
                )

                # Try to parse as JSON, fallback to raw text
                try:
                    security_payload = json.loads(response_text)
                    security_content = json.dumps(security_payload, indent=2)
                except json.JSONDecodeError:
                    security_payload = {"raw_security": response_text}
                    security_content = response_text

            # Save security artifact
            artifact_id = await self.save_artifact(
                artifact_type="security",
                content=security_content,
                metadata={
                    "task_id": task.task_id,
                    "development_length": len(development_content),
                    "architecture_length": len(architecture_content),
                    "qa_length": len(qa_content),
                    "parseable_json": "raw_security" not in security_payload,
                },
            )

            await self.log_event("info", f"Security review completed successfully: {artifact_id}")

            # Return result
            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "security": security_payload,
                    "artifact_id": artifact_id,
                    "next_stage": "documentation",
                },
                artifacts=[artifact_id],
                metadata={
                    "vulnerabilities_count": len(security_payload.get("vulnerabilities", [])),
                    "recommendations_count": len(
                        security_payload.get("security_recommendations", [])
                    ),
                    "parseable_json": "raw_security" not in security_payload,
                },
            )

            await self.notify_completion(result)
            return result

        except Exception as e:
            await self.log_event(
                "error",
                f"Security review failed: {type(e).__name__}: {str(e) or repr(e)}",
            )

            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                output={},
                artifacts=[],
                error=str(e),
            )

            await self.notify_completion(result)
            return result

    def _build_security_system_prompt(self) -> str:
        """Build system prompt for security review."""
        return """You are an expert Security Engineer and Application Security Specialist with deep expertise in identifying and mitigating security vulnerabilities.

Your role is to conduct comprehensive security reviews and vulnerability assessments based on development plans, architecture, and QA strategies.

## Your Expertise:
- Deep understanding of OWASP Top 10 and CWE Top 25 vulnerabilities
- Experience with security testing methodologies (SAST, DAST, penetration testing)
- Knowledge of authentication, authorization, and cryptography best practices
- Expertise in secure coding practices and threat modeling
- Understanding of compliance requirements (GDPR, SOC 2, HIPAA, PCI-DSS)
- Experience with security tools and vulnerability scanners

## Security Output (JSON format):
{
  "security_audit": {
    "audit_date": "YYYY-MM-DD",
    "audit_scope": "description",
    "security_level": "low-risk|medium-risk|high-risk",
    "overall_rating": "A|B|C|D|F",
    "summary": "brief summary"
  },
  "vulnerabilities": [
    {
      "vulnerability_id": "SEC-XXX",
      "severity": "critical|high|medium|low",
      "category": "category",
      "title": "vulnerability title",
      "description": "detailed description",
      "affected_components": ["components"],
      "cwe_id": "CWE-XXX",
      "cvss_score": 0.0-10.0,
      "exploit_likelihood": "high|medium|low",
      "impact": "potential impact",
      "recommendation": "how to fix",
      "mitigation_priority": "critical|high|medium|low",
      "estimated_effort": "time estimate"
    }
  ],
  "security_recommendations": [
    {
      "category": "category",
      "priority": "high|medium|low",
      "recommendation": "recommendation text",
      "rationale": "why this matters",
      "implementation_guidance": "how to implement"
    }
  ],
  "compliance_assessment": {
    "standards_evaluated": ["standards"],
    "owasp_top_10_coverage": {},
    "recommendations": ["recommendations"]
  },
  "security_best_practices": {
    "implemented": ["practices"],
    "missing": ["practices"]
  },
  "penetration_testing": {
    "recommended_scope": ["areas"],
    "timing": "when to conduct",
    "frequency": "how often"
  },
  "security_metrics": {
    "vulnerabilities_by_severity": {},
    "estimated_remediation_effort": "hours",
    "security_debt_score": 0.0-10.0
  },
  "next_steps": ["prioritized steps"]
}

## Security Review Principles:
- **Defense in depth**: Multiple layers of security controls
- **Least privilege**: Minimal access rights for users and systems
- **Fail securely**: Handle errors without exposing sensitive information
- **Zero trust**: Verify explicitly, assume breach
- **Secure by default**: Security enabled out of the box

## Guidelines:
- Identify specific, actionable vulnerabilities with clear remediation steps
- Prioritize based on risk (severity × likelihood × impact)
- Provide practical recommendations aligned with the development approach
- Reference industry standards (OWASP, CWE, CVSS)
- Focus on high-impact security improvements"""

    def _build_security_user_prompt(
        self, development_content: str, architecture_content: str, qa_content: str, prd_content: str
    ) -> str:
        """Build user prompt for security review."""
        prompt = f"""Conduct a comprehensive security review based on this development plan:

{development_content}
"""

        if architecture_content.strip():
            prompt += f"""

And this architecture:

{architecture_content}
"""

        if qa_content.strip():
            prompt += f"""

And this QA strategy:

{qa_content}
"""

        if prd_content.strip():
            prompt += f"""

And this PRD (for context):

{prd_content}
"""

        prompt += """

Please create a detailed security audit in JSON format following the structure provided.
Focus on:
- Identifying specific vulnerabilities with clear severity ratings
- Providing actionable remediation recommendations
- Assessing compliance with security standards
- Recommending security best practices
- Prioritizing security improvements by risk

Make it practical and aligned with the development approach."""

        return prompt
