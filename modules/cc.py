import discord
from discord.ext import commands
from lib import config
import aiohttp
from lib.utils import sql, Check, Forbidden, NoReg, Maintaining

def has_no_symbols():
    async def search(ctx):
        return "\\" not in ctx.message.content and '"' not in ctx.message.content and "'" not in ctx.message.content
    if not commands.check(search):
        raise commands.BadArgument
    else:
        return True

class CC(commands.Cog, name="지식 및 배우기"):
    def __init__(self, miya):
        self.miya = miya

    @commands.command(name="기억해", aliases=["배워"])
    @has_no_symbols()
    async def _learn(self, ctx, word, *, value):
        await sql(1, f"INSERT INTO `cc`(`word`, `description`, `user`) VALUES('{word}', '{value}', '{ctx.author.id}')")
        await ctx.send(f"Successfully learned {word}\n{value}")
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if (isinstance(error, commands.CommandNotFound)
              or isinstance(error, commands.NotOwner)
              or isinstance(error, commands.CheckFailure)):
            try:
                p = await Check.identify(ctx)
            except Exception as e:
                if isinstance(e, Forbidden):
                    await ctx.reply(str(e), embed=e.embed)
                elif isinstance(e, NoReg) or isinstance(e, Maintaining):
                    await ctx.reply(str(e))
                elif isinstance(e, commands.NoPrivateMessage):
                    return
            else:
                if p is True:
                    response_msg = None
                    url = config.PPBRequest
                    headers = {
                        "Authorization": config.PPBToken,
                        "Content-Type": "application/json",
                    }
                    query = ctx.message.content.replace("미야야 ", "")
                    async with aiohttp.ClientSession() as cs:
                        async with cs.post(
                                url,
                                headers=headers,
                                json={"request": {
                                    "query": query
                                }},
                        ) as r:
                            response_msg = await r.json()
                    msg = response_msg["response"]["replies"][0]["text"]
                    if msg != "앗, 저 이번 달에 할 수 있는 말을 다 해버렸어요 🤐 다음 달까지 기다려주실거죠? ☹️":
                        await self.miya.hook(config.Terminal,
                            f"PINGPONG Builder >\nUser - {ctx.author} ({ctx.author.id})\nSent - {query}\nReceived - {msg}\nGuild - {ctx.guild.name} ({ctx.guild.id})",
                            "명령어 처리 기록",
                            self.miya.user.avatar_url,
                        )
                        embed = discord.Embed(
                            title=msg,
                            description=
                            f"[Discord 지원 서버 접속하기](https://discord.gg/tu4NKbEEnn)\n[한국 디스코드 봇 리스트 하트 누르기](https://koreanbots.dev/bots/720724942873821316)",
                            color=0x5FE9FF,
                        )
                        embed.set_footer(
                            text="미야의 대화 기능은 https://pingpong.us/ 를 통해 제작되었습니다."
                        )
                        await ctx.reply(embed=embed)
                    else:
                        embed = discord.Embed(
                            title="💭 이런, 미야가 말풍선을 모두 사용한 모양이네요.",
                            description=
                            f"매월 1일에 말풍선이 다시 생기니 그 때까지만 기다려주세요!\n \n[Discord 지원 서버 접속하기](https://discord.gg/tu4NKbEEnn)\n[한국 디스코드 봇 리스트 하트 누르기](https://koreanbots.dev/bots/720724942873821316)",
                            color=0x5FE9FF,
                        )
                        embed.set_footer(
                            text="미야의 대화 기능은 https://pingpong.us/ 를 통해 제작되었습니다."
                        )
                        await ctx.reply(embed=embed)

def setup(miya):
    miya.add_cog(CC(miya))