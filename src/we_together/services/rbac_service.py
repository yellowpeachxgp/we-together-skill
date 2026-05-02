"""RBAC 角色 + scope 枚举 + token 校验。

最小模型：
  - Role: admin / editor / viewer
  - Scope: read / write / resolve_branch / federation_admin
  - token → role 映射由调用方提供（例如 env WE_TOGETHER_TOKENS）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Scope(str, Enum):
    READ = "read"
    WRITE = "write"
    RESOLVE_BRANCH = "resolve_branch"
    FEDERATION_ADMIN = "federation_admin"


ROLE_SCOPES: dict[Role, set[Scope]] = {
    Role.VIEWER: {Scope.READ},
    Role.EDITOR: {Scope.READ, Scope.WRITE, Scope.RESOLVE_BRANCH},
    Role.ADMIN: {Scope.READ, Scope.WRITE, Scope.RESOLVE_BRANCH, Scope.FEDERATION_ADMIN},
}


@dataclass
class TokenInfo:
    token: str
    role: Role
    tenant_id: str = "default"
    meta: dict = field(default_factory=dict)

    def has_scope(self, scope: Scope) -> bool:
        return scope in ROLE_SCOPES[self.role]


class TokenRegistry:
    def __init__(self) -> None:
        self._tokens: dict[str, TokenInfo] = {}

    def register(self, token: str, role: Role, tenant_id: str = "default") -> None:
        self._tokens[token] = TokenInfo(token=token, role=role, tenant_id=tenant_id)

    def lookup(self, token: str) -> TokenInfo | None:
        return self._tokens.get(token)

    def check(self, token: str, scope: Scope) -> bool:
        info = self._tokens.get(token)
        return bool(info and info.has_scope(scope))
