import os
import re
import time
import asyncio
from pathlib import Path
from typing import Optional

import discord
import pyttsx3
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ========= 全局状态 =========
guild_finish_words = {}     # 每个服务器默认结束词
guild_rates = {}            # 每个服务器语速
countdown_tasks = {}        # 每个服务器当前倒计时任务
AUDIO_DIR = Path("tts_cache")
AUDIO_DIR.mkdir(exist_ok=True)


# ========= 工具函数 =========
def get_finish_word(guild_id: int) -> str:
    return guild_finish_words.get(guild_id, "Zero")


def get_rate(guild_id: int) -> int:
    return guild_rates.get(guild_id, 210)


def tts_to_wav(text: str, output_path: str, rate: int = 210):
    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    engine.setProperty("volume", 1.0)

    # 尽量选英文语音
    try:
        voices = engine.getProperty("voices")
        for v in voices:
            name = (getattr(v, "name", "") or "").lower()
            vid = (getattr(v, "id", "") or "").lower()
            if "english" in name or "zira" in name or "david" in name or "en_" in vid:
                engine.setProperty("voice", v.id)
                break
    except Exception:
        pass

    engine.save_to_file(text, output_path)
    engine.runAndWait()
    engine.stop()


def ensure_audio_files(rate: int = 210):
    # 生成 1~30 的英文数字语音
    for i in range(1, 31):
        p = AUDIO_DIR / f"{i}_{rate}.wav"
        if not p.exists():
            print(f"生成语音文件: {p.name}")
            tts_to_wav(str(i), str(p), rate=rate)

    # 常用结束词
    for word in ["Go", "Start", "Begin", "Fire", "Zero"]:
        p = AUDIO_DIR / f"{word.lower()}_{rate}.wav"
        if not p.exists():
            print(f"生成语音文件: {p.name}")
            tts_to_wav(word, str(p), rate=rate)


def get_audio_path(text: str, rate: int) -> Path:
    text = text.strip()
    if text.isdigit():
        return AUDIO_DIR / f"{text}_{rate}.wav"
    return AUDIO_DIR / f"{text.lower()}_{rate}.wav"


async def join_author_voice(message: discord.Message) -> Optional[discord.VoiceClient]:
    if not message.author.voice or not message.author.voice.channel:
        await message.channel.send("先进入一个语音频道，再发送命令。")
        return None

    target_channel = message.author.voice.channel
    voice_client = message.guild.voice_client

    if voice_client is None:
        voice_client = await target_channel.connect(self_deaf=True, self_mute=False)
    elif voice_client.channel != target_channel:
        await voice_client.move_to(target_channel)

    return voice_client


async def ensure_connected(message: discord.Message) -> Optional[discord.VoiceClient]:
    voice_client = message.guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        return await join_author_voice(message)
    return voice_client


async def play_wav(voice_client: discord.VoiceClient, wav_path: Path):
    done = asyncio.Event()

    def after_playing(error):
        if error:
            print(f"播放错误: {error}")
        client.loop.call_soon_threadsafe(done.set)

    source = discord.FFmpegPCMAudio(str(wav_path))
    voice_client.play(source, after=after_playing)
    await done.wait()


async def stop_current_audio(guild: discord.Guild):
    vc = guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await asyncio.sleep(0.05)


# ========= 倒计时任务 =========
async def run_countdown(message: discord.Message, start: int, finish_word: str):
    guild_id = message.guild.id
    rate = get_rate(guild_id)
    ensure_audio_files(rate=rate)

    vc = await ensure_connected(message)
    if not vc:
        return

    await message.channel.send(f"开始倒计时：{start}")

    # ready_word = "Ready"
    # ready_path = get_audio_path(ready_word, rate)
    # if not ready_path.exists():
    #     tts_to_wav(ready_word, str(ready_path), rate=rate)
    #
    # await play_wav(vc, ready_path)
    # await asyncio.sleep(0.3)

    start_time = time.perf_counter()

    for index, n in enumerate(range(start, 0, -1)):
        target_time = start_time + index * 1.0

        now = time.perf_counter()
        if now < target_time:
            await asyncio.sleep(target_time - now)

        wav_path = get_audio_path(str(n), rate)
        await play_wav(vc, wav_path)

    finish_path = get_audio_path(finish_word, rate)
    if not finish_path.exists():
        tts_to_wav(finish_word, str(finish_path), rate=rate)

    await play_wav(vc, finish_path)


# ========= 事件 =========
@client.event
async def on_ready():
    print(f"已登录：{client.user} (id={client.user.id})")
    print("音频缓存目录：", AUDIO_DIR.resolve())
    ensure_audio_files(rate=210)
    print("预生成语音完成。")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if not message.guild:
        return

    content = message.content.strip()
    guild_id = message.guild.id

    # 进入语音频道
    if content == "!summon":
        vc = await join_author_voice(message)
        if vc:
            await message.channel.send(f"已进入语音频道：{vc.channel.name}")
        return

    # 离开语音频道
    if content == "!leave":
        task = countdown_tasks.get(guild_id)
        if task and not task.done():
            task.cancel()
            await stop_current_audio(message.guild)

        if message.guild.voice_client:
            await message.guild.voice_client.disconnect()
            await message.channel.send("已离开语音频道。")
        else:
            await message.channel.send("我当前不在语音频道里。")
        return

    # 查看状态
    if content == "!status":
        vc = message.guild.voice_client
        task = countdown_tasks.get(guild_id)
        running = bool(task and not task.done())

        if vc and vc.is_connected():
            await message.channel.send(
                f"我在语音频道：{vc.channel.name} | finish word: {get_finish_word(guild_id)} | rate: {get_rate(guild_id)} | running: {running}"
            )
        else:
            await message.channel.send("我当前不在语音频道。")
        return

    # 设置结束词
    if content.startswith("!setfinish "):
        finish_word = content[len("!setfinish "):].strip()
        if not finish_word:
            await message.channel.send("用法：!setfinish Go")
            return

        guild_finish_words[guild_id] = finish_word
        await message.channel.send(f"结束词已设置为：{finish_word}")
        return

    # 设置语速
    if content.startswith("!setrate "):
        value = content[len("!setrate "):].strip()
        if not value.isdigit():
            await message.channel.send("用法：!setrate 210")
            return

        rate = int(value)
        if rate < 150 or rate > 260:
            await message.channel.send("语速请设置在 150 到 260 之间。")
            return

        guild_rates[guild_id] = rate
        ensure_audio_files(rate=rate)
        await message.channel.send(f"语速已设置为：{rate}")
        return

    # 直接播报
    if content.startswith("!say "):
        text = content[len("!say "):].strip()
        if not text:
            await message.channel.send("用法：!say Hello everyone")
            return

        # 打断当前倒计时
        task = countdown_tasks.get(guild_id)
        if task and not task.done():
            task.cancel()
            await stop_current_audio(message.guild)

        vc = await ensure_connected(message)
        if not vc:
            return

        rate = get_rate(guild_id)
        temp_path = get_audio_path(text, rate)

        if not temp_path.exists():
            tts_to_wav(text, str(temp_path), rate=rate)

        await play_wav(vc, temp_path)
        return

    # 开始倒计时
    if content.startswith("!countdown"):
        m = re.match(r"^!countdown\s+(\d+)(?:\s+(.+))?$", content)
        if not m:
            await message.channel.send("用法：!countdown 30 或 !countdown 30 Start")
            return

        start = int(m.group(1))
        finish_word = m.group(2).strip() if m.group(2) else get_finish_word(guild_id)

        if start < 1 or start > 30:
            await message.channel.send("当前版本支持 1 到 30 秒。")
            return

        current_task = countdown_tasks.get(guild_id)
        if current_task and not current_task.done():
            await message.channel.send("当前已经有一个倒计时在运行。可用 !restart 重新开始，或 !stop 停止。")
            return

        task = asyncio.create_task(run_countdown(message, start, finish_word))
        countdown_tasks[guild_id] = task
        return

    # 重新开始倒计时：立刻打断并重新开始
    if content.startswith("!restart"):
        m = re.match(r"^!restart\s+(\d+)(?:\s+(.+))?$", content)
        if not m:
            await message.channel.send("用法：!restart 10 或 !restart 10 Start")
            return

        start = int(m.group(1))
        finish_word = m.group(2).strip() if m.group(2) else get_finish_word(guild_id)

        if start < 1 or start > 30:
            await message.channel.send("当前版本支持 1 到 30 秒。")
            return

        current_task = countdown_tasks.get(guild_id)
        if current_task and not current_task.done():
            current_task.cancel()
            await stop_current_audio(message.guild)
            await asyncio.sleep(0.1)

        task = asyncio.create_task(run_countdown(message, start, finish_word))
        countdown_tasks[guild_id] = task
        await message.channel.send(f"已重新开始倒计时：{start}")
        return

    # 立刻停止
    if content == "!stop":
        current_task = countdown_tasks.get(guild_id)
        if current_task and not current_task.done():
            current_task.cancel()
            await stop_current_audio(message.guild)
            await message.channel.send("已停止当前倒计时。")
        else:
            await message.channel.send("当前没有进行中的倒计时。")
        return


client.run(TOKEN)