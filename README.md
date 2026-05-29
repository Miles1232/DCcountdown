# Discord 语音倒计时 Bot

这是一个基于 `discord.py` 的 Discord 语音频道倒计时机器人。机器人可以加入用户所在的语音频道，播放英文数字倒计时，并在结束时播放指定结束词，例如 `Go`、`Start` 或 `Zero`。

## 功能

- 加入或离开用户所在的 Discord 语音频道
- 播放 1 到 30 秒的语音倒计时
- 支持自定义倒计时结束词
- 支持调整 TTS 语速
- 支持直接播报一段文字
- 自动生成并缓存 TTS 音频到 `tts_cache/`

## 项目结构

```text
.
├── bot.py              # Discord bot 主程序
├── requirement.txt     # Python 依赖
├── .env                # 本地环境变量，不应提交到仓库
├── .gitignore
└── tts_cache/          # 自动生成的语音缓存
```

## 环境要求

- Python 3.10 或更高版本
- Discord Bot Token
- 系统可用的 FFmpeg
- Windows 上可用的 TTS 语音引擎，项目通过 `pyttsx3` 生成语音

## 安装

建议先创建虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```powershell
pip install -r requirement.txt
```

如果语音播放失败，请确认 FFmpeg 已安装并能在命令行中访问：

```powershell
ffmpeg -version
```

## 配置

在项目根目录创建 `.env` 文件，并写入 Discord Bot Token：

```env
DISCORD_TOKEN=你的机器人Token
```

在 Discord Developer Portal 中，请确保机器人已开启：

- Message Content Intent
- 需要加入语音频道和发送消息的服务器权限

## 运行

```powershell
python bot.py
```

首次启动时会预生成默认语速 `210` 的常用语音文件。运行过程中如果设置了新的语速，也会自动生成对应缓存。

## 命令

| 命令 | 说明 |
| --- | --- |
| `!summon` | 加入你当前所在的语音频道 |
| `!leave` | 离开语音频道，并停止当前倒计时 |
| `!status` | 查看机器人所在频道、结束词、语速和运行状态 |
| `!countdown 30` | 从 30 秒开始倒计时，结束词使用服务器默认值 |
| `!countdown 10 Start` | 从 10 秒开始倒计时，结束时播放 `Start` |
| `!restart 10` | 停止当前倒计时并重新开始 10 秒倒计时 |
| `!stop` | 停止当前倒计时 |
| `!setfinish Go` | 设置当前服务器默认结束词 |
| `!setrate 210` | 设置当前服务器语速，范围为 150 到 260 |
| `!say Hello` | 直接在语音频道播报指定文字 |

## 注意事项

- 当前倒计时支持 `1` 到 `30` 秒。
- `tts_cache/` 中的 `.wav` 文件是自动生成的缓存，可以删除，程序会在需要时重新生成。
- `.env` 包含敏感 Token，已经在 `.gitignore` 中忽略，不要提交到代码仓库。
- 如果机器人无法响应消息，通常是 Discord Developer Portal 中没有开启 Message Content Intent。
- 如果机器人能进频道但没有声音，通常需要检查 FFmpeg、PyNaCl 或语音频道权限。
