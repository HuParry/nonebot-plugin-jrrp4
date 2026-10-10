import tempfile
from pathlib import Path

import nonebot

# 隔离真实机器人数据；通过真实插件加载器验证依赖声明与初始化。
_test_directory = tempfile.TemporaryDirectory(prefix="jrrp-tests-")
_root = Path(_test_directory.name)
nonebot.init(
    driver="~none",
    localstore_data_dir=_root / "data",
    localstore_cache_dir=_root / "cache",
    localstore_config_dir=_root / "config",
)
assert nonebot.load_plugin("nonebot_plugin_jrrp4") is not None
