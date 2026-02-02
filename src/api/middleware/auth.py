"""KAN-73: Auth middleware for API."""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
import os
from datetime import datetime, timedelta

# Security configuration
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """Middleware for authenticating API requests."""

    def __init__(self, exempt_paths: Optional[list[str]] = None):
        """Initialize auth middleware.

        Args:
            exempt_paths: List of paths that don't require authentication
        """
        self.exempt_paths = exempt_paths or [
            "/docs",
            "/openapi.json",
            "/health",
            "/metrics/health",
        ]

    async def __call__(self, request: Request, call_next):
        """Process request through auth middleware.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from downstream handler

        Raises:
            HTTPException: If authentication fails
        """
        # Check if path is exempt
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Extract and verify token
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            # Parse "Bearer <token>"
            scheme, token = auth_header.split()

            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Verify JWT token
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            # Add user info to request state
            request.state.user_id = payload.get("user_id")
            request.state.username = payload.get("username")
            request.state.roles = payload.get("roles", [])

        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # Continue to next handler
        response = await call_next(request)
        return response


def create_token(user_id: str, username: str, roles: Optional[list[str]] = None) -> str:
    """Create a JWT token for a user.

    Args:
        user_id: Unique user identifier
        username: Username
        roles: Optional list of user roles

    Returns:
        JWT token string
    """
    payload = {
        "user_id": user_id,
        "username": username,
        "roles": roles or ["user"],
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> dict:
    """Verify a JWT token and return payload.

    Args:
        token: JWT token string

    Returns:
        Token payload

    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return payload


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = None
) -> dict:
    """Dependency to get current authenticated user.

    Args:
        credentials: HTTP bearer credentials

    Returns:
        User info from token

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    try:
        payload = verify_token(credentials.credentials)
        return payload
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


# Example usage in routes:
# from fastapi import Depends
# from src.api.middleware.auth import get_current_user
#
# @router.get("/protected")
# async def protected_endpoint(user: dict = Depends(get_current_user)):
#     return {"message": f"Hello {user['username']}"}
