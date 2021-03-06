import datetime
import locale
import os
import sys
import typing

import discord
from discord.ext import commands
from EZPaginator import Paginator

from lib import utils
from lib.utils import sql

locale.setlocale(locale.LC_ALL, "")

Check = utils.Check()


class Administration(commands.Cog, name="디버그"):
    """미야의 유지 관리 및 보수에 사용되는 것들"""
    def __init__(self, miya):
        self.miya = miya
        self.black = utils.Blacklisting()

    def is_manager():
        return commands.check(Check.mgr)

    def is_owner():
        return commands.check(Check.owner)

    @commands.command(name="탈주", hidden=True)
    @is_owner()
    async def _leave(self, ctx, guild_id: int):
        """
        미야야 탈주 < ID >


        지정한 서버에서 미야가 나갑니다.
        """
        guild = self.miya.get_guild(int(guild_id))
        if guild is not None:
            await guild.leave()
            await ctx.reply(f"🎬 **{guild.name}** 서버에서 퇴장했어요.")
        else:
            await ctx.reply("<:cs_no:659355468816187405> 서버를 발견하지 못했어요.")

    @commands.command(name="권한", hidden=True)
    @is_owner()
    async def _permission(self, ctx, user: discord.User, permission: str):
        """
        미야야 권한 < @유저 > < 설정할 권한 >


        유저의 권한을 설정합니다.
        """
        rows = await sql(0,
                         f"SELECT * FROM `users` WHERE `user` = '{user.id}'")
        if not rows:
            raise commands.BadArgument
        if permission not in [
                "Administrator",
                "Maintainer",
                "User",
                "Stranger",
                "Offender",
        ]:
            raise commands.BadArgument
        await sql(
            1,
            f"UPDATE `users` SET `permission` = '{permission}' WHERE `user` = '{user.id}'",
        )
        await ctx.reply(
            f"🎬 **{user}**의 권한이 업데이트되었어요.\n이전 권한 - `{rows[0][1]}`, 변경된 권한 - `{permission}`"
        )

    @commands.command(name="소유자", hidden=True)
    @is_manager()
    async def _check_owner(self, ctx, guild_id: int):
        """
        미야야 소유자 < 서버 ID >


        지정된 서버의 소유자를 조회해옵니다.
        """
        guild = self.miya.get_guild(int(guild_id))
        if guild is not None:
            await ctx.reply(
                f"🎬 {guild.name}의 소유자 : **{guild.owner}** ( {guild.owner.id} )"
            )

    @commands.command(name="블랙", hidden=True)
    @is_manager()
    async def blacklist_management(
        self,
        ctx,
        todo,
        user: discord.User,
        *,
        reason: typing.Optional[str] = "사유가 지정되지 않았습니다.",
    ):
        """
        미야야 블랙 < 추가 / 삭제 > < 유저 > [ 사유 ]


        유저의 미야 이용을 제한합니다.
        """
        if todo == "추가":
            await self.black.user(ctx, 0, user, reason)
            await ctx.reply(f"🎬 **{user}**의 권한이 `Offender`로 업데이트되었어요.")
        elif todo == "삭제":
            await self.black.user(ctx, 1, user, reason)
            await ctx.reply(f"🎬 **{user}**의 권한이 `Stranger`로 업데이트되었어요.")
        else:
            raise commands.BadArgument

    @commands.command(name="제한", hidden=True)
    @is_manager()
    async def _black_word(self, ctx, todo, *, word):
        """
        미야야 제한 < 추가 / 삭제 > < 단어 >


        자동 차단 단어를 관리합니다.
        """
        if todo == "추가":
            await self.black.word(ctx, 0, word)
            await ctx.reply(f"🎬 이제 `{word}` 단어를 사용 시 자동으로 차단돼요.")
        elif todo == "삭제":
            await self.black.word(ctx, 1, word)
            await ctx.reply(f"🎬 이제 `{word}` 단어를 더 이상 필터링하지 않아요.")
        else:
            raise commands.BadArgument

    @commands.group(name="조회", hidden=True)
    @is_manager()
    async def checkout(self, ctx):
        """
        미야야 조회 < 유저 / 단어 / 고유 > < 조회할 값 >


        값에 대해서 미야가 알고 있는 내용을 조회합니다.
        """
        if ctx.invoked_subcommand is None:
            raise commands.BadArgument

    @checkout.command(name="고유", hidden=True)
    @is_manager()
    async def _primary(self, ctx, number: int):
        """
        미야야 조회 고유 < 고유 번호 >


        고유 번호를 조회해 단어의 정보를 확인합니다.
        """
        rows = await sql(
            0,
            f"SELECT * FROM `cc` WHERE `no` = '{number}'")
        embed = discord.Embed(
            title=f"{number} 고유 번호 조회 결과",
            color=0x5FE9FF,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="입력 내용", value=rows[0][1], inline=False)
        embed.add_field(name="답장 내용", value=rows[0][2], inline=False)
        embed.add_field(name="가르친 유저의 ID", value=rows[0][3], inline=False)
        embed.add_field(name="비활성화되었나요?", value=rows[0][4], inline=False)
        embed.set_author(name="커맨드 목록", icon_url=self.miya.user.avatar_url)
        await ctx.send(embed=embed)

    @checkout.command(name="유저", hidden=True)
    @is_manager()
    async def _user(self, ctx, user_id):
        """
        미야야 조회 유저 < 유저 ID >


        해당 유저가 가르친 모든 내용을 조회합니다.
        """
        rows = await sql(
            0,
            f"SELECT * FROM `cc` WHERE `user` = '{user_id}' ORDER BY `no` ASC")
        embeds = []
        for i in range(len(rows)):
            embed = discord.Embed(
                title=f"{user_id}에 대한 지식 목록 ({i + 1} / {len(rows)})",
                color=0x5FE9FF,
                timestamp=datetime.datetime.utcnow(),
            )
            embed.add_field(name="지식 번호", value=rows[i][0], inline=False)
            embed.add_field(name="입력 내용", value=rows[i][1], inline=False)
            embed.add_field(name="답장 내용", value=rows[i][2], inline=False)
            embed.add_field(name="비활성화되었나요?", value=rows[i][4], inline=False)
            embed.set_author(name="커맨드 목록", icon_url=self.miya.user.avatar_url)
            embeds.append(embed)
        msg = await ctx.send(embed=embeds[0])
        page = Paginator(bot=self.miya, message=msg, embeds=embeds)
        await page.start()

    @checkout.command(name="단어", hidden=True)
    @is_manager()
    async def _word(self, ctx, word):
        """
        미야야 조회 단어 < 키워드 >


        키워드에 등록된 모든 내용을 조회합니다.
        """
        word.lower()
        rows = await sql(
            0, f"SELECT * FROM `cc` WHERE `word` = '{word}' ORDER BY `no` ASC")
        embeds = []
        for i in range(len(rows)):
            embed = discord.Embed(
                title=f"{word}에 대한 지식 목록 ({i + 1} / {len(rows)})",
                color=0x5FE9FF,
                timestamp=datetime.datetime.utcnow(),
            )
            embed.add_field(name="지식 번호", value=rows[i][0], inline=False)
            embed.add_field(name="답장 내용", value=rows[i][2], inline=False)
            embed.add_field(name="가르친 유저의 ID", value=rows[i][3], inline=False)
            embed.add_field(name="비활성화되었나요?", value=rows[i][4], inline=False)
            embed.set_author(name="커맨드 목록", icon_url=self.miya.user.avatar_url)
            embeds.append(embed)
        msg = await ctx.send(embed=embeds[0])
        page = Paginator(bot=self.miya, message=msg, embeds=embeds)
        await page.start()

    @commands.command(name="활성화", hidden=True)
    @is_manager()
    async def _active(self, ctx, number: int):
        """
        미야야 활성화 < 번호 >


        비활성화된 지식을 활성화합니다.
        """
        rows = await sql(0, f"SELECT * FROM `cc` WHERE `no` = '{number}'")
        if not rows:
            raise commands.BadArgument
        if rows[0][4] == "false":
            raise commands.BadArgument
        await sql(
            1, f"UPDATE `cc` SET `disabled` = 'false' WHERE `no` = '{number}'")
        await ctx.reply(f"🎬 #{rows[0][0]}의 {rows[0][1]}, 다시 활성화했어요.")

    @commands.command(name="비활성화", hidden=True)
    @is_manager()
    async def _remove(self, ctx, number: int):
        """
        미야야 비활성화 < 번호 >


        가르쳐진 지식을 비활성화합니다.
        """
        rows = await sql(0, f"SELECT * FROM `cc` WHERE `no` = '{number}'")
        if not rows:
            raise commands.BadArgument
        if rows[0][4] == "true":
            raise commands.BadArgument
        await sql(
            1, f"UPDATE `cc` SET `disabled` = 'true' WHERE `no` = '{number}'")
        await ctx.reply(f"🎬 #{rows[0][0]}의 {rows[0][1]}, 비활성화했어요.")

    @commands.command(name="점검", hidden=True)
    @is_owner()
    async def _maintain(self,
                        ctx,
                        *,
                        reason: typing.Optional[str] = "점검 중입니다."):
        """
        미야야 점검 [ 사유 ]


        점검 모드를 관리합니다.
        점검 모드가 활성화된 동안은 일반 유저의 명령어 사용이 중단됩니다.
        """
        msg = await ctx.reply(
            f":grey_question: 점검 모드를 어떻게 할까요?\n<:cs_yes:659355468715786262> - 켜기\n<:cs_no:659355468816187405> - 끄기"
        )
        await msg.add_reaction("<:cs_yes:659355468715786262>")
        await msg.add_reaction("<:cs_no:659355468816187405>")

        def check(reaction, user):
            return reaction.message.id == msg.id and user == ctx.author

        try:
            reaction, user = await self.miya.wait_for("reaction_add",
                                                      timeout=30,
                                                      check=check)
        except:
            await msg.delete()
        else:
            if str(reaction.emoji) == "<:cs_yes:659355468715786262>":
                operation = "true"
                await sql(1, f"UPDATE `miya` SET `maintained` = '{operation}'")
                await sql(1, f"UPDATE `miya` SET `mtr` = '{reason}'")
                await msg.edit(
                    content=f"<:cs_yes:659355468715786262> 점검 모드를 활성화했어요!")
            else:
                operation = "false"
                await sql(1, f"UPDATE `miya` SET `maintained` = '{operation}'")
                await msg.edit(
                    content=f"<:cs_yes:659355468715786262> 점검 모드를 비활성화했어요!")

    @commands.command(name="SQL", hidden=True)
    @is_owner()
    async def _sql(self, ctx, work, *, cmd):
        """
        미야야 SQL < fetch / commit > < SQL 명령 >


        SQL 구문을 실행하고, 리턴값을 반환합니다.
        """
        if work == "fetch":
            a = ""
            rows = await sql(0, cmd)
            for row in rows:
                a += f"{row}\n"
            if len(a) > 1900:
                await ctx.reply(
                    f"🎬 메시지 길이 제한으로 1900자까지만 출력되었어요. 모든 내용은 <#818512474960691200> 채널을 확인하세요.\n{a[:1900]}"
                )
                record = await self.miya.record(a)
                channel = self.miya.get_channel(818512474960691200)
                if isinstance(record, discord.File):
                    await channel.send(file=record)
                else:
                    await channel.send(record)
            else:
                await ctx.reply(a)
        elif work == "commit":
            result = await sql(1, cmd)
            await ctx.reply(f"🎬 SQL 명령문 실행 결과 : {result}")
        else:
            raise commands.BadArgument

    @commands.group(name="샤드", hidden=True)
    @is_owner()
    async def sharding(self, ctx):
        """
        미야야 샤드 < 켜기 / 끄기 / 재시작 > < 샤드 번호 >


        미야의 샤드를 관리합니다.
        """
        if ctx.invoked_subcommand is None:
            raise commands.BadArgument

    @sharding.command(name="켜기", hidden=True)
    @is_owner()
    async def _turn_on(self, ctx, shard: int):
        """
        미야야 샤드 켜기 < 샤드 번호 >


        미야의 샤드를 연결합니다.
        """
        sh = self.miya.get_shard(shard)
        if not sh:
            raise commands.BadArgument

        if sh.is_closed():
            await sh.connect()
            await ctx.reply(f"🎬 **{shard}**번 샤드를 켰어요.")
        else:
            await ctx.reply(f"🎬 **{shard}**번 샤드는 이미 켜져 있어요.")

    @sharding.command(name="끄기", hidden=True)
    @is_owner()
    async def _turn_off(self, ctx, shard: int):
        """
        미야야 샤드 끄기 < 샤드 번호 >


        미야의 샤드를 연결 해제합니다.
        """
        sh = self.miya.get_shard(shard)
        if not sh:
            raise commands.BadArgument

        if not sh.is_closed():
            await sh.disconnect()
            await ctx.reply(f"🎬 **{shard}**번 샤드를 껐어요.")
        else:
            await ctx.reply(f"🎬 **{shard}**번 샤드는 이미 꺼져 있어요.")

    @sharding.command(name="재시작", hidden=True)
    @is_owner()
    async def _turn_off(self, ctx, shard: int):
        """
        미야야 샤드 재시작 < 샤드 번호 >


        미야의 샤드를 연결 해제한 후 다시 연결합니다.
        """
        sh = self.miya.get_shard(shard)
        if not sh:
            raise commands.BadArgument

        await sh.reconnect()
        await ctx.reply(f"🎬 **{shard}**번 샤드를 재시작했어요.")

    @commands.command(name="재시작", hidden=True)
    @is_owner()
    async def _restart(self, ctx):
        """
        미야야 재시작


        현재 프로세스를 완전히 닫고 재시작합니다.
        """
        msg = await ctx.reply(
            f":grey_question: 미야를 정말로 재시작하시겠어요? 진행 중이던 작업이 사라질 수 있어요!\n<:cs_yes:659355468715786262> - 네\n<:cs_no:659355468816187405> - 아니오"
        )
        await msg.add_reaction("<:cs_yes:659355468715786262>")
        await msg.add_reaction("<:cs_no:659355468816187405>")

        def check(reaction, user):
            return reaction.message.id == msg.id and user == ctx.author

        try:
            reaction, user = await self.miya.wait_for("reaction_add",
                                                      timeout=30,
                                                      check=check)
        except:
            await msg.delete()
        else:
            if str(reaction.emoji) == "<:cs_yes:659355468715786262>":
                await msg.edit(content="🎬 미야가 곧 재시작됩니다...")
                os.execl(sys.executable, sys.executable, *sys.argv)
            else:
                await msg.delete()

    @commands.command(name="종료", hidden=True)
    @is_owner()
    async def _shutdown(self, ctx):
        """
        미야야 종료


        미야를 로그아웃시키고 프로세스를 닫습니다.
        """
        msg = await ctx.reply(
            f":grey_question: 미야를 정말로 종료하시겠어요? 진행 중이던 작업이 사라질 수 있어요!\n<:cs_yes:659355468715786262> - 예\n<:cs_no:659355468816187405> - 아니오"
        )
        await msg.add_reaction("<:cs_yes:659355468715786262>")
        await msg.add_reaction("<:cs_no:659355468816187405>")

        def check(reaction, user):
            return reaction.message.id == msg.id and user == ctx.author

        try:
            reaction, user = await self.miya.wait_for("reaction_add",
                                                      timeout=30,
                                                      check=check)
        except:
            await msg.delete()
        else:
            if str(reaction.emoji) == "<:cs_yes:659355468715786262>":
                await msg.edit(content="🎬 미야가 곧 종료됩니다...")
                await self.miya.logout()
            else:
                await msg.delete()


def setup(miya):
    miya.add_cog(Administration(miya))
