<div align="center">
  <a href="https://nonebot.dev/store"><img src="https://raw.githubusercontent.com/A-kirami/nonebot-plugin-template/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://raw.githubusercontent.com/A-kirami/nonebot-plugin-template/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>

# nonebot-plugin-jrrp4

_✨ 基于NoneBot2和OneBot V11的今日人品插件 ✨_

<a href="./LICENSE"><img src="https://img.shields.io/github/license/HuParry/nonebot-plugin-jrrp4.svg" alt="license"></a>
<a href="https://pypi.org/project/nonebot-plugin-jrrp4/"><img src="https://img.shields.io/pypi/v/nonebot-plugin-jrrp4.svg" alt="pypi"></a>
<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python">

</div>

## 📖 介绍

在 QQ 群聊中查询今日人品，返回 0～100 的数值和对应评价。同一账号在同一天得到相同结果，每天按机器人运行环境的本地日期更新。

支持查询自己、被 @ 的群成员和机器人，也支持通过配置名单调整指定账号的人品范围。

仅支持群聊，查询者群等级需达到10级。

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-jrrp4

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-jrrp4
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-jrrp4
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-jrrp4
</details>
<details>
<summary>conda</summary>

    conda install nonebot-plugin-jrrp4
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_jrrp4"]

</details>

## ⚙️ 配置

无需必填配置。在机器人项目的 `.env` 或实际使用的 `.env.prod` 等环境配置文件中添加以下可选配置，重启机器人生效。示例见 [.env.example](./.env.example)。

| 配置项 | 必填 | 默认值 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `JRRP_HIGH_LIST` | 否 | `[]` | `list[str]` | 人品偏高的 QQ 号列表，通常调整到 75～100 |
| `JRRP_LOW_LIST` | 否 | `[]` | `list[str]` | 人品偏低的 QQ 号列表，通常调整到 0～40 |

```dotenv
JRRP_HIGH_LIST=["123456789", "987654321"]
JRRP_LOW_LIST=["111222333"]
```

QQ 号需使用字符串形式的 JSON 数组。账号同时出现在两个列表时，优先应用 `JRRP_HIGH_LIST`。当原始计算结果直接命中 100 分时，不应用名单调整，因此低人品名单中的账号也可能获得 100 分。

## 🎉 使用

### 指令表

以下示例假设机器人配置 `COMMAND_START=["/"]`；实际前缀以机器人配置为准。`今日人品` 是 `jrrp` 的别名，可在所有示例中替换使用。

| 指令 | 权限 | 需要 @ | 范围 | 说明 |
| --- | --- | --- | --- | --- |
| `/jrrp` | 群等级 ≥ 10 的成员 | 否 | 群聊 | 查询自己今日人品 |
| `/jrrp @成员` | 群等级 ≥ 10 的成员 | 是，@目标成员 | 群聊 | 查询被 @ 成员，可一次 @ 多人 |
| `/jrrp @机器人` | 群等级 ≥ 10 的成员 | 是，@机器人 | 群聊 | 查询机器人今日人品 |

@ 需使用 QQ 的实际 @ 消息，纯文本 QQ 号不会触发查询。查询者等级不足时会提示“你的群聊等级不到10级，不告诉你今日人品！”。当消息被适配器识别为发给机器人（`to_me`）时，优先查询机器人自身。

### 回复示例

```text
你今天的人品值是：88/100！为"大吉"，太牛了，您今天人品爆发了！
```

## 📦 发布说明

仓库提供 [PyPI 发布工作流](./.github/workflows/pypi-publish.yml)，使用 PEP 621 格式的 [pyproject.toml](./pyproject.toml) 构建 wheel 和源码包，并在上传前校验包信息。

需要维护者自行完成的远程配置：

1. 将仓库发布到 `HuParry/nonebot-plugin-jrrp4`，并将本地 Git remote 指向自己的仓库。
2. 在 [PyPI](https://pypi.org/manage/account/#api-tokens) 创建 API Token，并在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加名为 `PYPI_API_TOKEN` 的 Repository secret。
3. 发布新版本前修改 `pyproject.toml` 中的 `project.version` 和插件 `__plugin_meta__.extra` 中的 `version`，保持一致，并提交代码。
4. 创建并推送对应版本的标签，触发工作流。例如当前版本：

```bash
git tag v0.2.3
git push origin v0.2.3
```

标签版本必须与 `project.version` 一致，允许使用 `v` 前缀。工作流也可在 GitHub Actions 中手动运行；同一 PyPI 版本不能重复上传。

如需提交 NoneBot 插件商店，维护者还需按 [官方发布指引](https://nonebot.dev/docs/developer/plugin-publishing) 操作；项目名为 `nonebot-plugin-jrrp4`，插件模块名为 `nonebot_plugin_jrrp4`。

## 📄 开源协议

本项目采用 [MIT License](./LICENSE)。
