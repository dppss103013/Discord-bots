import discord
from discord.ext import commands
import asyncio
import yt_dlp

intents = discord.Intents.default()
intents.message_content = True  # 必須啟用，否則 bot 無法讀取指令內容

bot = commands.Bot(command_prefix='!', intents=intents)

# yt_dlp 設定
ytdl_format_options = {
    'format': 'bestaudio/best',
    'default_search': 'ytsearch1',  # 自動搜尋關鍵字，取第一個
    'quiet': True,
    'noplaylist': True,
}

ffmpeg_options = {
    'options': '-vn'  # 不載入影片
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

music_queue = []
auto_queue = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=oHg5SJYRHA0"
]
is_playing = False

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.title = data.get('title')
        self.url = data.get('webpage_url')

    @classmethod
    async def from_query(cls, query, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.event
async def on_ready():
    print(f'✅ 機器人已上線：{bot.user}')

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            await channel.connect()
        elif ctx.voice_client.channel != channel:
            await ctx.voice_client.move_to(channel)
    else:
        await ctx.send("⚠️ 請先進入一個語音頻道。")

async def play_next(ctx):
    global is_playing
    if music_queue:
        next_query = music_queue.pop(0)
    elif auto_queue:
        next_query = auto_queue.pop(0)
        auto_queue.append(next_query)
    else:
        is_playing = False
        return

    try:
        player = await YTDLSource.from_query(next_query, loop=bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f'🎶 播放中：**{player.title}**\n🔗 {player.url}')
        is_playing = True
    except Exception as e:
        print(f'❌ 播放錯誤: {e}')
        await ctx.send("❌ 播放失敗，可能找不到音樂或格式錯誤。")
        is_playing = False

@bot.command()
async def play(ctx, *, query):
    global is_playing
    print(f'🔍 收到 !play 指令，搜尋：{query}')

    if ctx.author.voice is None:
        await ctx.send("⚠️ 你必須先進入語音頻道。")
        return

    if ctx.voice_client is None:
        await ctx.invoke(join)

    music_queue.append(query)
    await ctx.send(f"✅ 已加入播放清單：{query}")

    if not is_playing:
        await play_next(ctx)

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ 已暫停播放")

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ 繼續播放")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭ 已跳過目前音樂。")

@bot.command()
async def stop(ctx):
    global is_playing, music_queue
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        music_queue.clear()
        is_playing = False
        await ctx.send("🛑 已停止播放並離開語音頻道。")

# 將你的機器人 Token 貼在這裡
bot.run("111")
