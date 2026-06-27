"""
角色权限系统
定义每个角色可以执行的操作
"""

# 角色定义
ROLES = {
    "ADMIN": "管理员",
    "DIRECTOR": "科室主任",
    "REVIEWER": "审核员",
    "TECHNICIAN": "检验师",
}

# 权限定义
# 格式: { "权限名": "说明" }
PERMISSIONS = {
    "specimen:create": "创建标本",
    "specimen:receive": "接收标本",
    "specimen:view": "查看标本",
    "result:enter": "录入结果",
    "result:review": "审核结果",
    "result:view": "查看结果",
    "report:review": "审核报告",
    "report:print": "打印报告",
    "report:view": "查看报告",
    "user:manage": "管理员工",
    "base_data:edit": "编辑基础数据",
    "qc:manage": "质控管理",
    "audit:view": "查看操作日志",
    "instrument:manage": "管理仪器",
}

# 角色-权限映射
ROLE_PERMISSIONS = {
    "ADMIN": list(PERMISSIONS.keys()),  # 管理员拥有所有权限

    "DIRECTOR": [
        "specimen:create", "specimen:receive", "specimen:view",
        "result:enter", "result:review", "result:view",
        "report:review", "report:print", "report:view",
        "user:manage",
        "base_data:edit", "qc:manage", "audit:view",
        "instrument:manage",
    ],

    "REVIEWER": [
        "specimen:create", "specimen:receive", "specimen:view",
        "result:enter", "result:review", "result:view",
        "report:review", "report:print", "report:view",
        "qc:manage",
    ],

    "TECHNICIAN": [
        "specimen:create", "specimen:receive", "specimen:view",
        "result:enter", "result:view",
        "report:view", "report:print",
        "qc:manage",
    ],
}


def has_permission(role: str, permission: str) -> bool:
    """检查角色是否有某权限"""
    perms = ROLE_PERMISSIONS.get(role, [])
    return permission in perms


def get_role_permissions(role: str) -> list[str]:
    """获取角色的所有权限"""
    return ROLE_PERMISSIONS.get(role, [])


def check_permission_or_raise(role: str, permission: str):
    """检查权限，无权限则抛出异常"""
    from fastapi import HTTPException
    if not has_permission(role, permission):
        perm_desc = PERMISSIONS.get(permission, permission)
        raise HTTPException(403, f"权限不足：需要「{perm_desc}」权限")
