import datetime
import locale

import discord
from discord import Webhook, AsyncWebhookAdapter
import typing
import koreanbots
from discord.ext import commands
from pytz import timezone
from pytz import utc

import config
import aiomysql
import aiohttp
from bs4 import BeautifulSoup

locale.setlocale(locale.LC_ALL, "")

class Forbidden(commands.CheckFailure):
    def __init__(self, embed):
        self.embed = embed
        super().__init__(
            "<a:ban_guy:761149578216603668> https://discord.gg/tu4NKbEEnn")


class NoReg(commands.CheckFailure):
    def __init__(self):
        super().__init__(
            "<:cs_id:659355469034422282> 미야와 대화하시려면, 먼저 이용 약관에 동의하셔야 해요.\n`미야야 가입` 명령어를 사용하셔서 가입하실 수 있어요!"
        )

class Maintaining(commands.CheckFailure):
    def __init__(self, reason):
        super().__init__(
            f"<:cs_protect:659355468891947008> 지금은 미야와 대화하실 수 없어요.\n점검 중 : {reason}"
        )

class Miya(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.koreanbots = koreanbots.Client(self, config.DBKRToken)

    async def hook(self, url, content, name: typing.Optional[str] = None, avatar: typing.Optional[str] = None):
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(url, adapter=AsyncWebhookAdapter(session))
            await webhook.send(content, username=name, avatar_url=avatar)

    async def get_rank(self):
        num = 0
        while True:
            num += 1
            response = await self.koreanbots.getBots(num)
            data = [x.name for x in response]
            if "미야" in data:
                index = data.index("미야")
                result = 9 * (num - 1) + (index + 1)
                return result

    async def sql(self, type: int, sql: str):
        o = await aiomysql.connect(
            host=config.MySQL["host"],
            port=config.MySQL["port"],
            user=config.MySQL["username"],
            password=config.MySQL["password"],
            db=config.MySQL["schema"],
            autocommit=True,
        )
        c = await o.cursor()
        try:
            await c.execute(sql)
            if type == 0:
                rows = await c.fetchall()
                o.close()
                return rows
            o.close()
            return "processed"
        except Exception as e:
            o.close()
            return e

    def localize(self, time):
        KST = timezone("Asia/Seoul")
        abc = utc.localize(time).astimezone(KST)
        return abc.strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
    
    async def hangang(self):
        async with aiohttp.ClientSession() as cs:
            async with cs.get("http://hangang.dkserver.wo.tc") as r:
                response = await r.json(content_type=None)
                temp = None
                time = (response["time"]).split(" ")[0]
                if "." in response["temp"]:
                    temp = int(response["temp"].split(".")[0])
                else:
                    temp = int(response["temp"])
                return [temp, time]
    
    async def corona(self):
        async with aiohttp.ClientSession() as cs:
            async with cs.get("http://ncov.mohw.go.kr/") as r:
                html = await r.text()
                soup = BeautifulSoup(html, "lxml")
                data = soup.find("div", class_="liveNum")
                num = data.findAll("span", class_="num")
                corona_info = [corona_num.text for corona_num in num]
                return corona_info
    
    async def identify(self, ctx, miya):
        if ctx.channel.type == discord.ChannelType.private:
            await self.terminal(
                f"On Directs >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}",
                "명령어 처리 기록",
                miya.user.avatar_url,
            )
            raise commands.NoPrivateMessage

        manage = None
        mrows = await self.sql(0, f"SELECT * FROM `users` WHERE `user` = {ctx.author.id}")
        if mrows[0][1] == "Maintainer" or mrows[0][1] == "Administrator":
            manage = True
        maintain = await self.sql(0, f"SELECT * FROM `miya` WHERE `miya` = '{miya.user.id}'")
        if maintain[0][1] == "true" and not manage:
            raise Maintaining(maintain[0][2])
        reason, admin, time, banned, forbidden = None, None, None, None, None
        words = await self.sql(0, "SELECT * FROM `forbidden`")
        for word in words:
            if word[0] in ctx.message.content:
                forbidden = True
                banned = word[0]
        users = await self.sql(0, 
            f"SELECT * FROM `users` WHERE `user` = '{ctx.author.id}'")
        rows = await self.sql(0, 
            f"SELECT * FROM `blacklist` WHERE `id` = '{ctx.author.id}'")
        if rows:
            if manage is not True:
                reason = rows[0][1]
                admin = miya.get_user(int(rows[0][2]))
                time = rows[0][3]
                await self.hook(config.Terminal,
                    f"Blocked User >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                    "명령어 처리 기록",
                    miya.user.avatar_url,
                )
            else:
                await ctx.send("당신은 차단되었지만, 관리 권한으로 명령어를 실행했습니다.")
                await self.hook(config.Terminal,
                    f"Manager Bypassed >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                    "명령어 처리 기록",
                    miya.user.avatar_url,
                )
                return True
        elif forbidden is True:
            if manage is not True:
                reason = f"부적절한 언행 **[Auto]** - {banned}"
                admin = miya.user
                time = self.localize(datetime.datetime.utcnow())
                await self.sql(1, 
                    f"INSERT INTO `blacklist`(`id`, `reason`, `admin`, `datetime`) VALUES('{ctx.author.id}', '{reason}', '{admin.id}', '{time}')"
                )
                await self.hook(config.Blacklist,
                    f"New Block >\nVictim - {ctx.author.id}\nAdmin - {admin} ({admin.id})\nReason - {reason}",
                    "제한 기록",
                    miya.user.avatar_url,
                )
                await self.hook(config.Terminal,
                    f"Forbidden >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                    "명령어 처리 기록",
                    miya.user.avatar_url,
                )
            else:
                await ctx.send("해당 단어는 차단 대상이나, 관리 권한으로 명령어를 실행했습니다.")
                await self.hook(config.Terminal,
                    f"Manager Bypassed >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                    "명령어 처리 기록",
                    miya.user.avatar_url,
                )
                return True
        elif not users and ctx.command.name != "가입":
            await self.hook(config.Terminal,
                f"Cancelled >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                "명령어 처리 기록",
                miya.user.avatar_url,
            )
            raise NoReg()
        else:
            await self.hook(config.Terminal,
                f"Processed >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                "명령어 처리 기록",
                miya.user.avatar_url,
            )
            return True
        embed = discord.Embed(
            title=f"이런, {ctx.author}님은 차단되셨어요.",
            description=f"""
차단에 관해서는 지원 서버를 방문해주세요.
사유 : {reason}
관리자 : {admin}
차단 시각 : {time}
            """,
            timestamp=datetime.datetime.utcnow(),
            color=0xFF3333,
        )
        embed.set_author(name="이용 제한", icon_url=miya.user.avatar_url)
        raise Forbidden(embed)


intents = discord.Intents(
    guilds=True,
    members=True,
    bans=True,
    emojis=True,
    integrations=True,
    webhooks=True,
    invites=True,
    voice_states=True,
    presences=False,
    messages=True,
    reactions=True,
    typing=True,
)
miya = Miya(
    shard_count=3,
    command_prefix="미야야 ",
    description="다재다능한 Discord 봇, 미야.",
    help_command=None,
    chunk_guilds_at_startup=True,
    intents=intents,
)


def load_modules(miya):
    failed = []
    exts = [
        "modules.general",
        "modules.events",
        "modules.settings",
        "modules.admin",
        "modules.mods",
        "modules.register",
#        "modules.log",
#        "modules.eco",
        "jishaku",
    ]

    for ext in exts:
        try:
            miya.load_extension(ext)
        except Exception as e:
            print(f"{e.__class__.__name__}: {e}")
            failed.append(ext)

    return failed


@miya.check
async def process(ctx):
    p = await miya.identify(ctx, ctx.bot)
    return p


load_modules(miya)
miya.run(config.BotToken)
