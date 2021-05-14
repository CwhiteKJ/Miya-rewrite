import datetime
import typing

import aiohttp
import aiomysql
import discord
from bs4 import BeautifulSoup
from discord import AsyncWebhookAdapter
from discord import Webhook
from discord.ext import commands
from pytz import timezone
from pytz import utc

from lib import config


class Forbidden(commands.CheckFailure):
    def __init__(self):
        super().__init__(
            "<a:ban_guy:761149578216603668> 현재 미야 이용이 제한되셨어요, 자세한 내용은 `미야야 문의`를 사용해 문의해주세요."
        )


class NoReg(commands.CheckFailure):
    def __init__(self):
        super().__init__(
            "<:cs_id:659355469034422282> 미야와 대화하시려면, 먼저 이용 약관에 동의하셔야 해요.\n`미야야 가입` 명령어를 사용하셔서 가입하실 수 있어요!"
        )


class Maintaining(commands.CheckFailure):
    def __init__(self, reason):
        super().__init__(
            f"<:cs_protect:659355468891947008> 지금은 미야와 대화하실 수 없어요.\n```{reason}```"
        )


async def sql(type: int, sql: str):
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
        return "SUCCESS"
    except Exception as e:
        o.close()
        raise e


class Hook:
    async def terminal(self, target, content, name, avatar):
        url = None
        if target == 1:
            url = config.Blacklist
        elif target == 0:
            url = config.Terminal
        else:
            raise discord.NotFound
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(url,
                                       adapter=AsyncWebhookAdapter(session))
            await webhook.send(f"```{content}```",
                               username=name,
                               avatar_url=avatar)

    async def send(self, url, content, name, avatar):
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(url,
                                       adapter=AsyncWebhookAdapter(session))
            await webhook.send(content, username=name, avatar_url=avatar)


class Get:
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


class Blacklisting:
    def __init__(self):
        self.get = Get()
        self.hook = Hook()

    async def user(self, ctx, task, user: discord.User, reason: str):
        time = self.get.localize(datetime.datetime.utcnow())
        if task == 0:
            await sql(
                1,
                f"UPDATE `users` SET `permission` = 'Offender'",
            )
            await self.hook.terminal(
                1,
                f"Added Block >\nBlocked - {user.id}\nAdmin - {ctx.author} ({ctx.author.id})\nReason - {reason}",
                "제한 기록",
                ctx.bot.user.avatar_url,
            )
            try:
                embed = discord.Embed(
                    title=f"이런, {user}님은 이용이 제한되셨어요.",
                    description=f"""
자세한 내용은 `미야야 문의`를 사용해 문의해주세요.
사유 : {reason}
관리자 : {ctx.author}
차단 시각 : {time}
                    """,
                    timestamp=datetime.datetime.utcnow(),
                    color=0xFF3333,
                )
                embed.set_author(name="이용 제한",
                                 icon_url=ctx.bot.user.avatar_url)
                await user.send(
                    f"<a:ban_guy:761149578216603668> {user.mention}",
                    embed=embed)
            except:
                pass
        elif task == 1:
            await sql(
                1,
                f"UPDATE `users` SET `permission` = 'Stranger' WHERE `user` = '{user.id}'",
            )
            await self.hook.terminal(
                1,
                f"Removed Block >\nUnblocked - {user.id}\nAdmin - {ctx.author} ({ctx.author.id})",
                "제한 기록",
                ctx.bot.user.avatar_url,
            )
        else:
            raise commands.BadArgument

    async def word(self, ctx, task, word):
        if task == 0:
            await sql(1, f"INSERT INTO `forbidden`(`word`) VALUES('{word}')")
            await self.hook.terminal(
                1,
                f"New Forbidden >\nAdmin - {ctx.author} ({ctx.author.id})\nPhrase - {word}",
                "제한 기록",
                ctx.bot.user.avatar_url,
            )
        elif task == 1:
            await sql(1, f"DELETE FROM `forbidden` WHERE `word` = '{word}'")
            await self.hook.terminal(
                1,
                f"Removed Forbidden >\nAdmin - {ctx.author} ({ctx.author.id})\nPhrase - {word}",
                "제한 기록",
                ctx.bot.user.avatar_url,
            )
        else:
            raise commands.BadArgument


class Check:
    def __init__(self):
        self.hook = Hook()
        self.black = Blacklisting()

    async def explicit(self, ctx):
        words = await sql(0, "SELECT * FROM `forbidden`")
        for word in words:
            if word[0] in ctx.message.content:
                return {"Explicit": True, "Word": word[0]}
        return {"Explicit": False}

    async def block(self, ctx):
        user = await sql(
            0, f"SELECT * FROM `users` WHERE `user` = '{ctx.author.id}'")
        if not user:
            return False
        elif user[0][1] == "Offender":
            return True
        return False

    async def mgr(self, ctx):
        own = await ctx.bot.is_owner(ctx.author)
        if own:
            return True
        mrows = await sql(
            0, f"SELECT * FROM `users` WHERE `user` = {ctx.author.id}")
        if not mrows:
            return False
        return mrows[0][1] == "Maintainer" or mrows[0][1] == "Administrator"

    async def owner(self, ctx):
        own = await ctx.bot.is_owner(ctx.author)
        if own:
            return True
        mrows = await sql(
            0, f"SELECT * FROM `users` WHERE `user` = {ctx.author.id}")
        if not mrows:
            return False
        return mrows[0][1] == "Administrator"

    async def identify(self, ctx):
        if ctx.message.content.replace("미야야 ", "") == "문의":
            return True

        if ctx.channel.type == discord.ChannelType.private:
            await self.hook.terminal(
                0,
                f"On Directs >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}",
                "명령어 처리 기록",
                ctx.bot.user.avatar_url,
            )
            raise commands.NoPrivateMessage

        manage = await self.mgr(ctx)
        if manage:
            await self.hook.terminal(
                0,
                f"Maintainer >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                "명령어 처리 기록",
                ctx.bot.user.avatar_url,
            )
            return True

        maintain = await sql(
            0, f"SELECT * FROM `miya` WHERE `miya` = '{ctx.bot.user.id}'")
        user = await sql(
            0, f"SELECT * FROM `users` WHERE `user` = '{ctx.author.id}'")
        block = await self.block(ctx)
        explicit = await self.explicit(ctx)
        if maintain[0][1] == "true" and not manage:
            await self.hook.terminal(
                0,
                f"Cancelled due to maintaining >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}",
                "명령어 처리 기록",
                ctx.bot.user.avatar_url,
            )
            raise Maintaining(maintain[0][2])

        if block is True:
            await self.hook.terminal(
                0,
                f"Blocked User >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                "명령어 처리 기록",
                ctx.bot.user.avatar_url,
            )
            raise Forbidden
        elif explicit["Explicit"] is True:
            word = explicit["Word"]
            reason = f"부적절한 언행 **[Auto]** - {word}"
            admin = ctx.bot.user
            await self.black.user(0, ctx.author.id, admin, reason)
            await self.hook.terminal(
                1,
                f"New Block >\nVictim - {ctx.author.id}\nAdmin - {admin} ({admin.id})\nReason - {reason}",
                "제한 기록",
                ctx.bot.user.avatar_url,
            )
            await self.hook.terminal(
                0,
                f"Forbidden >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                "명령어 처리 기록",
                ctx.bot.user.avatar_url,
            )
            raise Forbidden
        elif not user and ctx.command.name != "가입":
            await sql(
                1,
                f"INSERT INTO `users`(`user`, `permission`, `money`) VALUES('{ctx.author.id}', 'Unregistered', '500')",
            )
            await self.hook.terminal(
                0,
                f"Cancelled >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                "명령어 처리 기록",
                ctx.bot.user.avatar_url,
            )
            raise NoReg
        elif user[0][1] == "Stranger" and ctx.command.name != "가입":
            await self.hook.terminal(
                0,
                f"Cancelled >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                "명령어 처리 기록",
                ctx.bot.user.avatar_url,
            )
            raise NoReg
        else:
            await self.hook.terminal(
                0,
                f"Processed >\nUser - {ctx.author} ({ctx.author.id})\nContent - {ctx.message.content}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                "명령어 처리 기록",
                ctx.bot.user.avatar_url,
            )
            return True
