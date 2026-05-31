from nonebot.adapters import Bot, Event
from nonebot.permission import Permission as NBPermission
from nonebot_plugin_permission import SUPER_USER as PERMISSION_SUPER_USER
from nonebot_plugin_permission import Permission as CithunPermission
from nonebot_plugin_permission import require_permission
from nonebot_plugin_permission import system as permission_system
from nonebot_plugin_uninfo import Uninfo

WORDCLOUD_PERMISSION_PREFIX = "command.wordcloud"
WORDCLOUD_QUERY_PERMISSION = f"{WORDCLOUD_PERMISSION_PREFIX}.query"
WORDCLOUD_QUERY_OTHER_PERMISSION = f"{WORDCLOUD_PERMISSION_PREFIX}.query_other"
WORDCLOUD_MASK_PERMISSION = f"{WORDCLOUD_PERMISSION_PREFIX}.mask"
WORDCLOUD_DEFAULT_MASK_PERMISSION = f"{WORDCLOUD_PERMISSION_PREFIX}.default_mask"
WORDCLOUD_SCHEDULE_PERMISSION = f"{WORDCLOUD_PERMISSION_PREFIX}.schedule"


permission_system.pre_assign(
    PERMISSION_SUPER_USER,
    f"{WORDCLOUD_PERMISSION_PREFIX}.*",
    CithunPermission("vma"),
)

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
mask_permission = NBPermission(check_mask_permission)
default_mask_permission = NBPermission(check_default_mask_permission)
schedule_permission = NBPermission(check_schedule_permission)


async def check_mask_manage_permission(event: Event, bot: Bot, sess: Uninfo) -> bool:
    return await check_mask_permission(
        event, bot, sess
    ) or await check_default_mask_permission(event, bot, sess)


mask_manage_permission = NBPermission(check_mask_manage_permission)
