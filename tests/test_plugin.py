import asyncio
import nonebot


def test_async_command_score_uses_persisted_engine():
    plugin = nonebot.get_plugin('nonebot_plugin_jrrp4')
    assert plugin.metadata.extra['version'] == '0.3.0'
    async def query():
        first, second = await asyncio.gather(
            plugin.module.get_jrrp('123456789'),
            plugin.module.get_jrrp('123456789'),
        )
        assert first == second
        assert 0 <= first <= 100
    asyncio.run(query())
