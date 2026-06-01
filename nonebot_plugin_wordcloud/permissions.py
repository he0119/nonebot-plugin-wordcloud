from typing import TYPE_CHECKING

from nonebot.permission import Permission as NBPermission
from nonebot_plugin_permission import SUPER_USER as PERMISSION_SUPER_USER
from nonebot_plugin_permission import Permission as CithunPermission
from nonebot_plugin_permission import require_permission
from nonebot_plugin_permission import system as permission_system

if TYPE_CHECKING:
    from nonebot_plugin_user.models import UserSession

WORDCLOUD_PERMISSION_PREFIX = "command.wordcloud"
WORDCLOUD_ADMIN_ROLE_LEVEL = 10
WORDCLOUD_QUERY_PERMISSION = f"{WORDCLOUD_PERMISSION_PREFIX}.query"
WORDCLOUD_QUERY_OTHER_PERMISSION = f"{WORDCLOUD_PERMISSION_PREFIX}.query_other"
WORDCLOUD_MASK_PERMISSION = f"{WORDCLOUD_PERMISSION_PREFIX}.mask"
WORDCLOUD_DEFAULT_MASK_PERMISSION = f"{WORDCLOUD_PERMISSION_PREFIX}.default_mask"
WORDCLOUD_SCHEDULE_PERMISSION = f"{WORDCLOUD_PERMISSION_PREFIX}.schedule"
WORDCLOUD_ADMIN_ATTACH_PERMISSIONS = frozenset(
    {
        WORDCLOUD_QUERY_OTHER_PERMISSION,
        WORDCLOUD_MASK_PERMISSION,
        WORDCLOUD_SCHEDULE_PERMISSION,
    }
)


permission_system.pre_assign(
    PERMISSION_SUPER_USER,
    f"{WORDCLOUD_PERMISSION_PREFIX}.*",
    CithunPermission("vma"),
)


def _is_wordcloud_admin_attach_permission(resource: str) -> bool:
    """判断资源是否属于需要群管动态放行的词云权限。"""
    return resource in WORDCLOUD_ADMIN_ATTACH_PERMISSIONS


@permission_system.attach(_is_wordcloud_admin_attach_permission)
async def _attach_uninfo_admin_permission(
    _user,
    _resource: str,
    context,
    _current_mask: CithunPermission,
    _permission_lookup,
):
    """为 uninfo 识别出的群主/管理员补充词云受限权限。

    attach 返回值只参与本次权限计算，不会写入权限插件的 ACL 表。
    """
    if context is None:
        return CithunPermission.NONE

    session: UserSession | None = context.get("session")
    member = session.session.member if session else None
    role = member.role if member else None
    if role and role.level >= WORDCLOUD_ADMIN_ROLE_LEVEL:
        return CithunPermission("v-a")

    return CithunPermission.NONE


check_query_permission = require_permission(WORDCLOUD_QUERY_PERMISSION)
check_query_other_permission = require_permission(
    WORDCLOUD_QUERY_OTHER_PERMISSION, default_available=False
)
check_mask_permission = require_permission(
    WORDCLOUD_MASK_PERMISSION, default_available=False
)
check_default_mask_permission = require_permission(
    WORDCLOUD_DEFAULT_MASK_PERMISSION, default_available=False
)
check_schedule_permission = require_permission(
    WORDCLOUD_SCHEDULE_PERMISSION, default_available=False
)

query_permission = NBPermission(check_query_permission)
query_other_permission = NBPermission(check_query_other_permission)
mask_permission = NBPermission(check_mask_permission)
default_mask_permission = NBPermission(check_default_mask_permission)
schedule_permission = NBPermission(check_schedule_permission)
mask_manage_permission = mask_permission | default_mask_permission
