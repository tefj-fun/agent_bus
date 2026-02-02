"""KAN-74: RBAC for HITL actions."""

from enum import Enum
from typing import List, Optional
from fastapi import HTTPException, status


class Role(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"  # Full access to all operations
    OPERATOR = "operator"  # Can approve/reject HITL, manage jobs
    DEVELOPER = "developer"  # Can submit jobs, view results
    VIEWER = "viewer"  # Read-only access


class Permission(str, Enum):
    """Permissions for various actions."""

    # Job permissions
    JOB_SUBMIT = "job:submit"
    JOB_VIEW = "job:view"
    JOB_CANCEL = "job:cancel"
    JOB_DELETE = "job:delete"

    # HITL permissions
    HITL_APPROVE = "hitl:approve"
    HITL_REJECT = "hitl:reject"
    HITL_VIEW = "hitl:view"

    # Memory permissions
    MEMORY_WRITE = "memory:write"
    MEMORY_READ = "memory:read"
    MEMORY_DELETE = "memory:delete"

    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_CONFIG = "admin:config"
    ADMIN_METRICS = "admin:metrics"


# Role to permissions mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        # All permissions
        Permission.JOB_SUBMIT,
        Permission.JOB_VIEW,
        Permission.JOB_CANCEL,
        Permission.JOB_DELETE,
        Permission.HITL_APPROVE,
        Permission.HITL_REJECT,
        Permission.HITL_VIEW,
        Permission.MEMORY_WRITE,
        Permission.MEMORY_READ,
        Permission.MEMORY_DELETE,
        Permission.ADMIN_USERS,
        Permission.ADMIN_CONFIG,
        Permission.ADMIN_METRICS,
    ],
    Role.OPERATOR: [
        Permission.JOB_SUBMIT,
        Permission.JOB_VIEW,
        Permission.JOB_CANCEL,
        Permission.HITL_APPROVE,
        Permission.HITL_REJECT,
        Permission.HITL_VIEW,
        Permission.MEMORY_WRITE,
        Permission.MEMORY_READ,
    ],
    Role.DEVELOPER: [
        Permission.JOB_SUBMIT,
        Permission.JOB_VIEW,
        Permission.JOB_CANCEL,
        Permission.HITL_VIEW,
        Permission.MEMORY_WRITE,
        Permission.MEMORY_READ,
    ],
    Role.VIEWER: [
        Permission.JOB_VIEW,
        Permission.HITL_VIEW,
        Permission.MEMORY_READ,
    ],
}


class RBACManager:
    """Role-Based Access Control manager."""

    @staticmethod
    def get_role_permissions(role: Role) -> List[Permission]:
        """Get permissions for a role.

        Args:
            role: User role

        Returns:
            List of permissions
        """
        return ROLE_PERMISSIONS.get(role, [])

    @staticmethod
    def has_permission(user_roles: List[str], required_permission: Permission) -> bool:
        """Check if user has a specific permission.

        Args:
            user_roles: List of user role strings
            required_permission: Permission to check

        Returns:
            True if user has permission
        """
        for role_str in user_roles:
            try:
                role = Role(role_str)
                permissions = ROLE_PERMISSIONS.get(role, [])
                if required_permission in permissions:
                    return True
            except ValueError:
                # Invalid role string
                continue

        return False

    @staticmethod
    def require_permission(
        user_roles: List[str],
        required_permission: Permission,
        resource_id: Optional[str] = None,
    ) -> None:
        """Require a permission or raise HTTPException.

        Args:
            user_roles: List of user roles
            required_permission: Required permission
            resource_id: Optional resource identifier for error message

        Raises:
            HTTPException: If user lacks permission
        """
        if not RBACManager.has_permission(user_roles, required_permission):
            detail = f"Permission denied: {required_permission.value} required"
            if resource_id:
                detail += f" for resource {resource_id}"

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )


# Dependency for route permission checking
def require_permission(permission: Permission):
    """Create a dependency that requires a specific permission.

    Usage:
        @router.post("/hitl/approve", dependencies=[Depends(require_permission(Permission.HITL_APPROVE))])
        async def approve_hitl(request: Request, ...):
            ...

    Args:
        permission: Required permission

    Returns:
        Dependency function
    """
    async def permission_checker(request) -> None:
        # Get user roles from request state (set by auth middleware)
        user_roles = getattr(request.state, "roles", [])

        if not user_roles:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        RBACManager.require_permission(user_roles, permission)

    return permission_checker


# Example route with RBAC:
# from fastapi import Depends, Request
# from src.api.rbac import require_permission, Permission
#
# @router.post("/hitl/{hitl_id}/approve")
# async def approve_hitl(
#     hitl_id: str,
#     request: Request,
#     _: None = Depends(require_permission(Permission.HITL_APPROVE))
# ):
#     # Only users with HITL_APPROVE permission can access this
#     return {"status": "approved"}
