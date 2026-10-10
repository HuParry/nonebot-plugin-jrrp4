from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.plugin import on_command
from nonebot.params import CommandArg
from nonebot import get_plugin_config, require
import asyncio
from typing import List
from .config import Config
from .luck import LuckEngine

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as localstore

from nonebot.plugin import PluginMetadata

jrrp_config = get_plugin_config(Config)


__plugin_meta__ = PluginMetadata(
    name="今日人品",
    description="bot给你预测今天的人品值",
    usage="群聊发送 jrrp / 今日人品；可 @成员 查询对方，@机器人 查询机器人。",
    type="application",
    homepage="https://github.com/HuParry/nonebot-plugin-jrrp4",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "unique_name": "jrrp",
        "example": "今日人品 / jrrp",
        "version": "0.3.0",
    },
)

jrrp = on_command("jrrp", aliases = {"今日人品"}, priority = 50, block = True)
message: List[dict] = [
	{
		"expr": "jrrp >= 98",
		"start": "！！！！！你今天的人品值是：",
		"end": "！为\"吉吉国王\"，这个吉吉国王称号，非你莫属了呀~"
	},
	{
		"expr": "jrrp >= 85",
		"end": "！为\"大吉\"，太牛了，您今天人品爆发了！"
	},
	{
		"expr": "jrrp >= 75",
		"end": "！为\"吉\"，今天人品很好，快告诉我你是怎么做到的"
	},
	{
		"expr": "jrrp >= 65",
		"end": "！为\"半吉\"，今天人品不错，继续保持"
	},
	{
		"expr": "jrrp >= 53",
		"end": "！为\"小吉\"，今天人品还行，不过可以更上一个台阶"
	},
	{
		"expr": "jrrp >= 36",
		"end": "！为\"末小吉\"，今天人品一般般，继续加油"
	},
	{
		"expr": "jrrp >= 21",
		"end": "！为\"末吉\"，今天人品低，凑合着过吧，希望你明天能有点进步"
	},
	{
		"expr": "jrrp >= 1",
		"end": "！为\"凶\"，今天人品有点低，换个星球呆一天吧…"
	},
	{
		"expr": "jrrp == 0",
		"end": "，……这个银河系可能已经不适合你了……"
	}
]

high_list = jrrp_config.jrrp_high_list #列表中的人品爆发！
low_list = jrrp_config.jrrp_low_list #列表中的人品极低！
min_level = jrrp_config.jrrp_min_level
luck_engine = LuckEngine(localstore.get_plugin_data_file("luck.sqlite3"), high_list, low_list)
@jrrp.handle()
async def jrrp_handle(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    user_id = event.user_id
    group_id = event.group_id
    if min_level > 0:
        member_info = await bot.get_group_member_info(
            user_id=user_id,
            group_id=group_id
        )
        level = int(member_info.get('level'))
        if level < min_level:
            await jrrp.finish(f'你的群聊等级不到{min_level}级，不告诉你今日人品！')
    if event.is_tome():
        id = event.self_id
        jrrp_num = await get_jrrp(str(id))
        result = await get_msgme(jrrp_num)
        reply = MessageSegment.reply(event.message_id)
        await jrrp.send(reply + result)
    elif len(args) == 0:
        id = event.get_user_id()
        jrrp_num = await get_jrrp(str(id))
        result = await get_msg(jrrp_num)
        reply = MessageSegment.reply(event.message_id)
        await jrrp.send(reply + result)
    else:
        for msg_seg in args:
            if msg_seg.type == "at":
                id = msg_seg.data["qq"]
                jrrp_num = await get_jrrp(str(id))
                result = await get_msghe(jrrp_num)
                await jrrp.send(MessageSegment.at(str(id)) + result)
                await asyncio.sleep(1)
            else:
                print(1)

async def get_jrrp(string: str):
    return await asyncio.to_thread(luck_engine.score, string)

async def get_msg(jrrp):
    start: str = "你今天的人品值是："
    end: str = "……"
    for msg_obj in message:
        if eval(msg_obj["expr"]):
            start = msg_obj.get("start") if msg_obj.get("start") else start
            end = msg_obj.get("end") if msg_obj.get("end") else end
            lumsg = start + f'{str(jrrp)}/100' + end
            return lumsg

async def get_msgme(jrrp):
    start: str = "我今天的人品值是："
    end: str = "……"
    for msg_obj in message:
        if eval(msg_obj["expr"]):
            start = msg_obj.get("start") if msg_obj.get("start") else start
            end = msg_obj.get("end") if msg_obj.get("end") else end
            lumsg = start + f'{str(jrrp)}/100' + end
            return lumsg

async def get_msghe(jrrp):
    start: str = "今天的人品值是："
    end: str = "……"
    for msg_obj in message:
        if eval(msg_obj["expr"]):
            start = msg_obj.get("start") if msg_obj.get("start") else start
            end = msg_obj.get("end") if msg_obj.get("end") else end
            lumsg = start + f'{str(jrrp)}/100' + end
            return lumsg
