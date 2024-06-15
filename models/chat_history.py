from datetime import datetime, timedelta
from typing import Any, List, Literal, Optional, Tuple, Union

from tortoise import fields
from tortoise.functions import Count

from services.db_context import Model


class ChatHistory(Model):

    id = fields.IntField(pk=True, generated=True, auto_increment=True)
    """自增id"""
    user_id = fields.CharField(255)
    """用户id"""
    group_id = fields.CharField(255, null=True)
    """群聊id"""
    text = fields.TextField(null=True)
    """文本内容"""
    plain_text = fields.TextField(null=True)
    """纯文本"""
    create_time = fields.DatetimeField(auto_now_add=True)
    """创建时间"""
    bot_id = fields.CharField(255, null=True)
    """bot记录id"""

    class Meta:
        table = "chat_history"
        table_description = "聊天记录数据表"

    @classmethod
    async def get_group_msg_rank(
        cls,
        gid: Union[int, str],
        limit: int = 10,
        order: str = "DESC",
        date_scope: Optional[Tuple[datetime, datetime]] = None,
    ) -> List["ChatHistory"]:
        """
        说明:
            获取排行数据
        参数:
            :param gid: 群号
            :param limit: 获取数量
            :param order: 排序类型，desc，des
            :param date_scope: 日期范围
        """
        o = "-" if order == "DESC" else ""
        query = cls.filter(group_id=str(gid))
        if date_scope:
            query = query.filter(create_time__range=date_scope)
        return list(
            await query.annotate(count=Count("user_id"))
            .order_by(o + "count")
            .group_by("user_id")
            .limit(limit)
            .values_list("user_id", "count")
        )  # type: ignore

    @classmethod
    async def get_group_first_msg_datetime(
        cls, group_id: Union[int, str]
    ) -> Optional[datetime]:
        """
        说明:
            获取群第一条记录消息时间
        参数:
            :param group_id: 群组id
        """
        if (
            message := await cls.filter(group_id=str(group_id))
            .order_by("create_time")
            .first()
        ):
            return message.create_time

    @classmethod
    async def get_message(
        cls,
        uid: Union[int, str],
        gid: Union[int, str],
        type_: Literal["user", "group"],
        msg_type: Optional[Literal["private", "group"]] = None,
        days: Optional[Union[int, Tuple[datetime, datetime]]] = None,
    ) -> List["ChatHistory"]:
        """
        说明:
            获取消息查询query
        参数:
            :param uid: 用户id
            :param gid: 群聊id
            :param type_: 类型，私聊或群聊
            :param msg_type: 消息类型，用户或群聊
            :param days: 限制日期
        """
        if type_ == "user":
            query = cls.filter(user_id=str(uid))
            if msg_type == "private":
                query = query.filter(group_id__isnull=True)
            elif msg_type == "group":
                query = query.filter(group_id__not_isnull=True)
        else:
            query = cls.filter(group_id=str(gid))
            if uid:
                query = query.filter(user_id=str(uid))
        if days:
            if isinstance(days, int):
                query = query.filter(
                    create_time__gte=datetime.now() - timedelta(days=days)
                )
            elif isinstance(days, tuple):
                query = query.filter(create_time__range=days)
        return await query.all()  # type: ignore

    @classmethod
    async def _run_script(cls):
        return [
            "alter table chat_history alter group_id drop not null;",  # 允许 group_id 为空
            "alter table chat_history alter text drop not null;",  # 允许 text 为空
            "alter table chat_history alter plain_text drop not null;",  # 允许 plain_text 为空
            "ALTER TABLE chat_history RENAME COLUMN user_qq TO user_id;",  # 将user_id改为user_id
            "ALTER TABLE chat_history ALTER COLUMN user_id TYPE character varying(255);",
            "ALTER TABLE chat_history ALTER COLUMN group_id TYPE character varying(255);",
            "ALTER TABLE chat_history ADD bot_id VARCHAR(255);",  # 添加bot_id字段
            "ALTER TABLE chat_history ALTER COLUMN bot_id TYPE character varying(255);",
        ]
