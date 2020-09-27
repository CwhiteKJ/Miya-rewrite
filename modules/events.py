import discord
from discord.ext import commands
import json
import aiohttp
from utils import data
from lib import config
import datetime


class handler(commands.Cog, name="이벤트 리스너"):
    def __init__(self, miya):
        self.miya = miya

    @commands.Cog.listener()
    async def on_ready(self):
        print(self.miya.user)
        print(self.miya.user.id)
        await self.miya.change_presence(
            status=discord.Status.idle, activity=discord.Game("'미야야 도움'이라고 말해보세요!")
        )
        print("READY")
        uptime_set = await data.update('miya', 'uptime', str(datetime.datetime.now()), 'botId', self.miya.user.id)
        print(f"Uptime Change :: {uptime_set}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            response_msg = None
            url = config.PPBRequest
            headers = {
                "Authorization": config.PPBToken,
                "Content-Type": "application/json",
            }
            query = ""
            for q in ctx.message.content.split(" ")[1:]:
                query += f"{q} "
            async with aiohttp.ClientSession() as cs:
                async with cs.post(
                    url,
                    headers=headers,
                    json={
                        "request": {"query": query}
                    },
                ) as r:
                    response_msg = await r.json()  
            msg = response_msg["response"]["replies"][0]["text"]
            print(f"Sent {query} to Ping Pong builder and got {msg}")
            embed = discord.Embed(
                title=msg,
                description=f"[Discord 지원 서버 접속하기](https://discord.gg/mdgaSjB)\n[한국 디스코드 봇 리스트 하트 누르기](https://koreanbots.dev/bots/miya)",
                color=0x5FE9FF,
            )
            embed.set_footer(text="Powered by https://pingpong.us/")
            await ctx.send(embed=embed)
        elif isinstance(error, commands.NotOwner):
            await ctx.send(f"{ctx.author.mention} 해당 명령어는 미야 관리자에 한해 사용이 제한됩니다.")
        elif isinstance(error, commands.MissingPermissions):
            mp = error.missing_perms
            p = ""
            if mp[0] == "administrator":
                p = "관리자"
            if mp[0] == "manage_guild":
                p = "서버 관리하기"
            if mp[0] == "kick_members":
                p = "멤버 추방하기"
            if mp[0] == "ban_members":
                p = "멤버 차단하기"
            if mp[0] == "manage_channels":
                p = "채널 관리하기"
            if mp[0] == "manage_roles":
                p = "역할 관리하기"
            if mp[0] == "manage_messages":
                p = "메시지 관리"
            await ctx.send(f"<:cs_no:659355468816187405> {ctx.author.mention} 당신은 이 명령어를 실행할 권한이 없어요.\n해당 명령어를 실행하려면 이 권한을 가지고 계셔야 해요. `{p}`")
        elif isinstance(error, commands.BotMissingPermissions):
            mp = error.missing_perms
            p = ""
            if mp[0] == "manage_webhooks":
                p = "웹후크 관리하기"
            if mp[0] == "kick_members":
                p = "멤버 추방하기"
            if mp[0] == "ban_members":
                p = "멤버 차단하기"
            if mp[0] == "manage_channels":
                p = "채널 관리하기"
            if mp[0] == "manage_roles":
                p = "역할 관리하기"
            if mp[0] == "manage_messages":
                p = "메시지 관리"
            await ctx.send(f"<:cs_no:659355468816187405> {ctx.author.mention} 명령어를 실행할 권한이 부족해 취소되었어요.\n해당 명령어를 실행하려면 미야에게 이 권한이 필요해요. `{p}`")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"<:cs_stop:665173353874587678> {ctx.author.mention} 잠시 기다려주세요. 해당 명령어를 사용하려면 {round(error.retry_after)}초를 더 기다리셔야 해요.\n해당 명령어는 `{error.cooldown.per}`초에 `{error.cooldown.rate}`번만 사용할 수 있어요.")
        else:
            print(f"An error occurred : {error}")
            await ctx.send(f"{ctx.author.mention} 오류 발생; 이 오류가 지속될 경우 Discord 지원 서버로 문의해주세요. https://discord.gg/mdgaSjB")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        print(f"Added to {guild.name} ( {guild.id} )")
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        print(f"Removed from {guild.name} ( {guild.id} )")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot == False:
            value = await data.load(table="memberNoti", find_column="guild", find_value=member.guild.id)
            if value is None:
                return
            else:
                channel = member.guild.get_channel(int(value[1]))
                if channel is not None and value[2] != "":
                    msg = value[2].replace("{member}", str(member.mention))
                    msg = msg.replace("{guild}", str(member.guild.name))
                    msg = msg.replace("{count}", str(member.guild.member_count))
                    await channel.send(msg)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.bot == False:
            value = await data.load(table="memberNoti", find_column="guild", find_value=member.guild.id)
            if value is None:
                return
            else:
                channel = member.guild.get_channel(int(value[1]))
                if channel is not None and value[3] != "":
                    msg = value[3].replace("{member}", str(member))
                    msg = msg.replace("{guild}", str(member.guild.name))
                    msg = msg.replace("{count}", str(member.guild.member_count))
                    await channel.send(msg)


def setup(miya):
    miya.add_cog(handler(miya))
