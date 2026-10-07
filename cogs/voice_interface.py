from __future__ import annotations
import discord
from discord.ext import commands
from discord import app_commands
import config
from discord.ext.commands.cooldowns import CooldownMapping
from config import *
from typing import Optional
from . import database_channel_operations as DB_CHANNEL_IO
import traceback
from logger import log_error , log_info





async def send(interaction:discord.Interaction, msg:str , ephemeral:bool = True)-> None: # sends message or send followup if response is already sent
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(msg, ephemeral=ephemeral)

async def send_embed(interaction:discord.Interaction, embed:discord.Embed , ephemeral:bool = True)-> None: # sends embed or send followup if response is already sent
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

# ──────────────────────────────────────────────
#  MODALS
# ──────────────────────────────────────────────

class RenameModal(discord.ui.Modal, title="Переименовать канал"):
    new_name = discord.ui.TextInput(
        label="Новое название канала",
        placeholder="например: уютный уголок",
        max_length=config.MAX_RENAME_CHARACTER_LIMIT,
        min_length=1,
    )

    def __init__(self, channel: discord.VoiceChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        await self.channel.edit(name=self.new_name.value)
        await send(interaction=interaction,msg=f"✅ Канал переименован в **{self.new_name.value}**")


class LimitModal(discord.ui.Modal, title="Лимит участников"):
    limit = discord.ui.TextInput(
        label="Лимит участников (0 = без лимита)",
        placeholder="Введите число от 0 до 99",
        max_length=2,
    )

    def __init__(self, channel: discord.VoiceChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        if not self.limit.value.isdigit():
            await send(interaction=interaction,msg="❌ Введите корректное число.", ephemeral=True)
            return
        
        value = min(int(self.limit.value), 99)
        await self.channel.edit(user_limit=value)
        label = "без лимита" if value == 0 else str(value)
        await send(interaction=interaction,msg=f"✅ Лимит участников установлен: **{label}**")


# ──────────────────────────────────────────────
#  USER SELECT VIEWS
# ──────────────────────────────────────────────

class InviteUserSelect(discord.ui.View):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(timeout=30)
        self.channel = channel

    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Найдите и выберите участника для приглашения…",
        min_values=1,
        max_values=1,
    )
    async def select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        target = interaction.guild.get_member(select.values[0].id)
        if not target:
            return await interaction.response.send_message(
                "❌ Участник не найден на этом сервере.", ephemeral=True
            )
        if target.bot:
            return await interaction.response.send_message(
                "❌ Нельзя приглашать ботов.", ephemeral=True
            )
        if target.voice and target.voice.channel == self.channel:
            return await interaction.response.send_message(
                "❌ Этот участник уже в вашем канале.", ephemeral=True
            )

        ow = self.channel.overwrites_for(target)
        ow.connect = True
        ow.view_channel = True
        await self.channel.set_permissions(target, overwrite=ow)

        invite_link = f"https://discord.com/channels/{interaction.guild.id}/{self.channel.id}"

        try:
            await target.send(
                f"Вас пригласили в канал **{self.channel.name}**.\n"
                f"Нажмите, чтобы зайти: {invite_link}"
            )
        except discord.Forbidden:
            pass

        await interaction.response.send_message(
            f"📨 **{target.display_name}** получил(а) приглашение.", ephemeral=True
        )


class TrustUserSelect(discord.ui.View):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(timeout=30)
        self.channel = channel

    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Найдите и выберите участника, которому доверяете…",
        min_values=1,
        max_values=1,
    )
    async def select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        target = interaction.guild.get_member(select.values[0].id)
        if not target:
            return await interaction.response.send_message(
                "❌ Участник не найден на этом сервере.", ephemeral=True
            )
        
        if target.id == interaction.user.id:
            return await interaction.response.send_message(
                "❌ Вы и так владелец этого канала.", ephemeral=True
            )
        ow = self.channel.overwrites_for(target)
        ow.connect = True
        ow.speak = True
        ow.stream = True
        ow.use_voice_activation = True
        ow.view_channel = True
        await self.channel.set_permissions(target, overwrite=ow)
        await interaction.response.send_message(
            f"✅ **{target.display_name}** теперь **доверенный участник**.", ephemeral=True
        )


class BanUserSelect(discord.ui.View):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(timeout=30)
        self.channel = channel

    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Найдите и выберите участника для бана…",
        min_values=1,
        max_values=1,
    )
    async def select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        target = interaction.guild.get_member(select.values[0].id)
        if not target:
            return await interaction.response.send_message(
                "❌ Участник не найден на этом сервере.", ephemeral=True
            )
        if target.id == interaction.user.id:
            return await interaction.response.send_message(
                "❌ Нельзя забанить самого себя.", ephemeral=True
            )
        if target.voice and target.voice.channel == self.channel:
            await target.move_to(None)
        ow = self.channel.overwrites_for(target)
        ow.connect = False
        ow.view_channel = False
        await self.channel.set_permissions(target, overwrite=ow)
        await interaction.response.send_message(
            f"🚫 **{target.display_name}** забанен(а) в вашем канале.",
            ephemeral=True,
        )



#────────────────REUSABLE MEMBER SELECT──────────────────────

def build_member_select(
    placeholder: str,
    options: list[discord.SelectOption],
    callback,
) -> discord.ui.View:
    class DynamicSelect(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)

        @discord.ui.select(placeholder=placeholder, options=options)
        async def _select(self, inner: discord.Interaction, select: discord.ui.Select):
            target = inner.guild.get_member(int(select.values[0]))
            await callback(inner, target)

    return DynamicSelect()

#─────────────Cooldown Manager──────────#

class CooldownManager:

    def  __init__(self):
        # key -> {id : Cooldown}
        self._mappings : dict[str,dict[int, commands.Cooldown]] = {}

    def _get_bucket_key(self,interaction:discord.Interaction,bucket_type:commands.BucketType)->int:
        """Extract bucket id according to bucket type"""
        match bucket_type:
            case commands.BucketType.user:
                return interaction.user.id
            case commands.BucketType.channel:
                return interaction.channel_id
            case commands.BucketType.guild:
                return interaction.guild_id
            case _:
                return interaction.channel_id

    def check(self,key: str,rate: int,per: float,interaction: discord.Interaction,bucket_type: commands.BucketType = commands.BucketType.channel) -> float | None:
        
        if key not in self._mappings:
            self._mappings[key] = {}

        bucket_id = self._get_bucket_key(interaction, bucket_type)

        if bucket_id not in self._mappings[key]:
            self._mappings[key][bucket_id] = commands.Cooldown(rate, per)

        return self._mappings[key][bucket_id].update_rate_limit()
    
    
    


#─────────────PANEL VIEW────────────────


class VoicePanelView(discord.ui.View):
    
    _cooldowns = CooldownManager() # shared across all instances 

    def __init__(self):
        super().__init__(timeout=None)
        

    # ── core checks ───────────────────────────

    def _is_guild(self,interaction: discord.Interaction) -> bool:
        return isinstance(interaction.guild, discord.Guild)

    async def _cooldown_response(self,interaction:discord.Interaction,time:float):
        cooldown_remaining = round(time)
        await interaction.response.send_message(f"⏳ Команда на перезарядке. Повторите через **{cooldown_remaining} с**.",ephemeral=True)

    def _get_trusted_members(self,channel:discord.VoiceChannel)-> tuple[list[discord.Member], list[discord.Member]]:

        """Returns (trusted_members, owner) from channel overwrites"""

        if not isinstance(channel,discord.VoiceChannel):
            return [] , []
        
        trusted = []
        owner = []

        for target, overwrite in channel.overwrites.items():
            
            if isinstance(target,discord.Member):
                if (overwrite.connect is True and 
                      overwrite.speak is True and 
                      overwrite.stream is True and 
                      overwrite.use_voice_activation is True and 
                      overwrite.view_channel is True and
                      overwrite.read_message_history is True): # making sure user have those permissiong given while voice channel creation
                    
                    owner.append(target)

                elif (overwrite.connect is True and 
                    overwrite.speak is True and 
                    overwrite.stream is True and 
                    overwrite.use_voice_activation is True and 
                    overwrite.view_channel is True): # making sure user have permission given when trusted
                    
                    trusted.append(target)
        
        return trusted , owner
    
    def _user_in_voice_channel_check(self,interaction:discord.Interaction) -> bool: # checks if user is in voice channel or not
        return bool(interaction.user.voice and interaction.user.voice.channel)

    def _is_owner(self,interaction: discord.Interaction) -> bool:
        if not interaction.guild_id:
            return False
    
        if not self._user_in_voice_channel_check(interaction): # main command handles the user in voice but still to prevent crashes we check user's voice status
            return False

        channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

        if not isinstance(channel,DB_CHANNEL_IO.Channel):
            return False
        
        if interaction.user.id == channel.owner_id:
            return True
        
        return False

    @discord.ui.button(emoji="🔒", style=discord.ButtonStyle.secondary,
                       custom_id="panel:lock", row=0)
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel = interaction.user.voice.channel 
            if not channel:
                return
            everyone = interaction.guild.default_role
            overwrite = channel.overwrites_for(everyone)

            if overwrite.connect is False: # verifying if voice channel isnt locked already to avoid unnecessary api calls
                await send(interaction=interaction,msg="Голосовой канал уже закрыт.")
                return        

            overwrite.connect = False
            await channel.set_permissions(everyone, overwrite=overwrite)

            await send(interaction=interaction,msg="🔒 Канал **закрыт**.")
            return

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : lock - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="🔓", style=discord.ButtonStyle.secondary,
                       custom_id="panel:unlock", row=1)
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel:discord.VoiceChannel = interaction.user.voice.channel

            if not channel:
                return
            
            ow = channel.overwrites_for(interaction.guild.default_role)
            if ow.connect is not False:
                await send(interaction=interaction,msg=f"Голосовой канал уже открыт.")
                return
            ow.connect = None # reset to guild default
            await channel.set_permissions(interaction.guild.default_role, overwrite=ow)
            await send(interaction=interaction,msg="🔓 Канал **открыт**.")

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : unlock - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="🙈", style=discord.ButtonStyle.secondary,
                       custom_id="panel:hide", row=0)
    async def hide(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel = interaction.user.voice.channel
            if not channel:
                return

            ow = channel.overwrites_for(interaction.guild.default_role)
            ow.view_channel = False
            ow.connect = False
            await channel.set_permissions(interaction.guild.default_role, overwrite=ow)
            await send(interaction=interaction,msg="🙈 Канал **скрыт**.")
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : hide - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="👁️", style=discord.ButtonStyle.secondary,
                       custom_id="panel:show", row=0)
    async def show(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel = interaction.user.voice.channel

            if not channel:
                return
            
            ow = channel.overwrites_for(interaction.guild.default_role)
            ow.view_channel = None
            ow.connect = None
            await channel.set_permissions(interaction.guild.default_role, overwrite=ow)
            await send(interaction=interaction,msg="👁️ Канал **виден всем**.")

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : show - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="✏️", style=discord.ButtonStyle.secondary,
                       custom_id="panel:rename", row=0)
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
        
            channel =  interaction.user.voice.channel

            if not channel:
                return

            retry_after = self._cooldowns.check("rename",1,float(RENAME_COOLDOWN),interaction)

            if retry_after:
                await self._cooldown_response(interaction,retry_after)
                return
            
            await interaction.response.send_modal(RenameModal(channel))
            return
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : rename - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="👥", style=discord.ButtonStyle.secondary,
                       custom_id="panel:limit", row=0)
    async def set_limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel = interaction.user.voice.channel

            if not channel:
                return

            await interaction.response.send_modal(LimitModal(channel))

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : set_limit - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="📨", style=discord.ButtonStyle.secondary,
                       custom_id="panel:invite", row=1)
    async def invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel = interaction.user.voice.channel

            if not channel:
                return

            await interaction.response.send_message("📨 Выберите участника для приглашения:",view=InviteUserSelect(channel),ephemeral=True)

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : invite - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="👢", style=discord.ButtonStyle.secondary,
                       custom_id="panel:kick", row=1)
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel = interaction.user.voice.channel

            if not channel:
                return

            members = [m for m in channel.members if m.id != interaction.user.id]
            if not members:
                await send(interaction=interaction,msg="❌ В вашем канале нет других участников.")
                return

            options = [
                discord.SelectOption(
                    label=m.display_name[:100],
                    description=f"@{m.name}",
                    value=str(m.id),
                )
                for m in members
            ]

            async def do_kick(inner: discord.Interaction, target: discord.Member):
                if target and target.voice and target.voice.channel == channel:
                    await target.move_to(None)
                    await send(interaction=inner,msg=f"👢 **{target.display_name}** исключён(а) из канала.")
                else:
                    await send(interaction=inner,msg="❌ Участника уже нет в вашем канале.")

            view = build_member_select("Выберите участника для исключения…", options, do_kick)
            await interaction.response.send_message(
                "Выберите участника, которого нужно исключить:", view=view, ephemeral=True
            )

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : kick - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="🚫", style=discord.ButtonStyle.secondary,
                       custom_id="panel:ban", row=2)
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel = interaction.user.voice.channel

            if not channel:
                return
            
            await interaction.response.send_message(
                "🚫 Выберите участника для бана:",
                view=BanUserSelect(channel),
                ephemeral=True,
            )

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : ban - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="✅", style=discord.ButtonStyle.secondary,
                       custom_id="panel:trust", row=1)
    async def trust(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel = interaction.user.voice.channel

            if not channel:
                return
            
            await interaction.response.send_message(
                "✅ Выберите участника, которому доверяете:",
                view=TrustUserSelect(channel),
                ephemeral=True,
            )

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : trust - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="⛔", style=discord.ButtonStyle.secondary,
                       custom_id="panel:untrust", row=1)
    async def untrust(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel = interaction.user.voice.channel

            if not channel:
                return

            trusted = [
                m for m in interaction.guild.members
                if m.id != interaction.user.id
                and channel.overwrites_for(m).connect is True 
                and channel.overwrites_for(m).speak is True
                and channel.overwrites_for(m).stream is True
                and channel.overwrites_for(m).use_voice_activation is True
                and channel.overwrites_for(m).view_channel is True
            ]
            if not trusted:
                return await interaction.response.send_message(
                    "❌ Доверенных участников нет.", ephemeral=True
                )

            options = [
                discord.SelectOption(
                    label=m.display_name[:100],
                    description=f"@{m.name}",
                    value=str(m.id),
                )
                for m in trusted[:25]
            ]

            async def do_untrust(inner: discord.Interaction, target: discord.Member):
                if target:
                    await channel.set_permissions(target, overwrite=None)
                    await inner.response.send_message(
                        f"⛔ **{target.display_name}** больше не **доверенный участник**.", ephemeral=True
                    )
                else:
                    await inner.response.send_message("❌ Участник не найден.", ephemeral=True)

            view = build_member_select("Выберите, у кого убрать доверие…", options, do_untrust)
            await interaction.response.send_message(
                "Выберите участника, у которого нужно убрать доверие:", view=view, ephemeral=True
            )

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : untrust - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="✔️", style=discord.ButtonStyle.secondary,
                       custom_id="panel:unblock", row=2)
    async def unblock(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel = interaction.user.voice.channel

            if not channel:
                return

            banned = [
                m for m in interaction.guild.members
                if not m.bot
                and channel.overwrites_for(m).connect is False
            ]
            if not banned:
                return await interaction.response.send_message(
                    "❌ Забаненных участников нет.", ephemeral=True
                )

            options = [
                discord.SelectOption(
                    label=m.display_name[:100],
                    description=f"@{m.name}",
                    value=str(m.id),
                )
                for m in banned[:25]
            ]

            async def do_unblock(inner: discord.Interaction, target: discord.Member):
                if target:
                    await channel.set_permissions(target, overwrite=None)
                    await inner.response.send_message(
                        f"✔️ **{target.display_name}** **разблокирован(а)**.", ephemeral=True
                    )
                else:
                    await inner.response.send_message("❌ Участник не найден.", ephemeral=True)

            view = build_member_select("Выберите участника для разбана…", options, do_unblock)
            await interaction.response.send_message(
                "Выберите участника для разбана:", view=view, ephemeral=True
            )

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : unblock - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary,
                       custom_id="panel:transfer", row=2)
    async def transfer(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel = interaction.user.voice.channel

            if not channel:
                return
        
            retry_after = self._cooldowns.check("transfer",1,float(CLAIM_TRANSFER_COOLDOWN),interaction)

            if retry_after:
                await self._cooldown_response(interaction,retry_after)
                return

            members = [m for m in channel.members if m.id != interaction.user.id]
            if not members:
                return await interaction.response.send_message(
                    "❌ В канале нет других участников для передачи прав.", ephemeral=True
                )

            options = [
                discord.SelectOption(
                    label=m.display_name[:100],
                    description=f"@{m.name}",
                    value=str(m.id),
                )
                for m in members if not m.bot
            ]

            async def do_transfer(inner: discord.Interaction, target: discord.Member):
                if target:
                    edit_status = DB_CHANNEL_IO.channel_edit(server_id=inner.user.voice.channel.guild.id,channel_id=inner.user.voice.channel.id,new_owner_id=target.id)
                    if not edit_status:
                        return

                    owner_overwrite = discord.PermissionOverwrite( # permission overwrites for voice channel owner 
                        connect=True,
                        read_message_history=True,
                        speak=True,
                        stream=True,
                        use_voice_activation=True,
                        view_channel=True
                    )

                    overwrites = {
                        target : owner_overwrite,
                        interaction.client.user: discord.PermissionOverwrite( # bot's permissions 
                            connect=True,
                            view_channel=True,
                            send_messages=True
                        )
                    }

                    channel_edit = {
                        'overwrites' : overwrites,
                        'user_limit' : 0
                    }

                    if not channel.name == f"🔥・костёр {target.display_name}":
                        channel_edit['name'] = f"🔥・костёр {target.display_name}"

                    await channel.edit(**channel_edit) # editing channel with one api call


                    await inner.response.send_message(
                        f"🔁 Права владельца переданы: **{target.display_name}**.", ephemeral=True
                    )
                else:
                    await inner.response.send_message("❌ Участник не найден.", ephemeral=True)

            view = build_member_select("Выберите нового владельца…", options, do_transfer)
            await interaction.response.send_message(
                "Выберите нового владельца канала:", view=view, ephemeral=True
            )
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : transfer - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="👑", style=discord.ButtonStyle.secondary,custom_id="panel:claim", row=2)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self._is_guild(interaction):
                await interaction.response.send_message("❌ Эта команда работает только на сервере",ephemeral=True)
                return

            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return
    
            channel = interaction.user.voice.channel

            owner = interaction.guild.get_member(voice_channel.owner_id)
    
            owner_overwrite = discord.PermissionOverwrite( # permission overwrites for voice channel owner 
                connect=True,
                read_message_history=True,
                speak=True,
                stream=True,
                use_voice_activation=True,
                view_channel=True
            )
    
            overwrites = {
                interaction.user : owner_overwrite,
                interaction.client.user: discord.PermissionOverwrite( # bot's permissions 
                    connect=True,
                    view_channel=True,
                    send_messages=True
                )
            }

            if interaction.user.id == owner.id:
                await send(interaction=interaction,msg="❌ Вы уже владелец этого голосового канала.")
                return
            
            owner_still_here = (
                owner
                and owner.voice
                and owner.voice.channel
                and owner.voice.channel.id == channel.id
            )
            if owner_still_here:
                return await interaction.response.send_message(
                    "❌ Владелец всё ещё в канале.", ephemeral=True
                )
    
            channel_edit = {
                'overwrites' : overwrites,
                'user_limit' : 0 # reset limit
            }
    
            if not channel.name == f"🔥・костёр {interaction.user.display_name}":
                channel_edit['name'] = f"🔥・костёр {interaction.user.display_name}"
    
            edit_status = DB_CHANNEL_IO.channel_edit(server_id=interaction.guild.id,channel_id=interaction.user.voice.channel.id,new_owner_id=interaction.user.id)
            if not edit_status:
                await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
                return
            
            await channel.edit(**channel_edit) # editing channel with one api call
            
            retry_after = self._cooldowns.check("claim",1,float(CLAIM_TRANSFER_COOLDOWN),interaction)
            
            if retry_after:
                await self._cooldown_response(interaction,retry_after)
                return
            
            await interaction.response.send_message(
                "👑 Вы **забрали** этот канал!", ephemeral=True
            )

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : claim - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @discord.ui.button(emoji="🗑️", style=discord.ButtonStyle.secondary,
                       custom_id="panel:delete", row=2)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self._is_guild(interaction):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self._user_in_voice_channel_check(interaction):
                await send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self._is_owner(interaction=interaction):
                await send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            channel = interaction.user.voice.channel

            if not channel:
                return

            class ConfirmView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=15)

                @discord.ui.button(label="Да, удалить", style=discord.ButtonStyle.danger)
                async def confirm(self, inner: discord.Interaction, btn: discord.ui.Button):
                    delete_status = DB_CHANNEL_IO.channel_delete(server_id=inner.guild_id,channel_id=inner.user.voice.channel.id)
                    if not delete_status:
                        return
                    await channel.delete()
                    await inner.response.send_message("🗑️ Канал удалён.", ephemeral=True)
                    self.stop()

                @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
                async def cancel(self, inner: discord.Interaction, btn: discord.ui.Button):
                    await inner.response.send_message("❌ Отменено.", ephemeral=True)
                    self.stop()

            await interaction.response.send_message(
                "⚠️ Вы уверены, что хотите **удалить** свой канал? Это действие нельзя отменить.",
                view=ConfirmView(),
                ephemeral=True,
            )
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : delete - file : voice_interface.py : Error Name - {error_name}",exc_info=exception_traceback)
            await send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return


# ────────────────INTERACTIVE PANEL────────────────

def build_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎙️ Панель голосового канала",
        description=(
            "Управляйте временным голосовым каналом с помощью кнопок ниже.\n"
            "Чтобы пользоваться кнопками, нужно находиться **в своём канале**.\n\u200b"
        ),
        color=0x5865F2,
    )
    embed.add_field(name="🔒 Закрыть",      value="Запретить другим заходить.",        inline=True)
    embed.add_field(name="🔓 Открыть",    value="Разрешить другим заходить.",             inline=True)
    embed.add_field(name="🙈 Скрыть",      value="Скрыть из списка каналов.",           inline=True)
    embed.add_field(name="👁️ Показать",      value="Вернуть в список каналов.",     inline=True)
    embed.add_field(name="✏️ Название",    value="Изменить название канала.",         inline=True)
    embed.add_field(name="👥 Лимит", value="Ограничить число участников (0 = без лимита).",  inline=True)
    embed.add_field(name="📨 Пригласить",    value="Найти и пригласить участника.",  inline=True)
    embed.add_field(name="👢 Выгнать",      value="Отключить участника от канала.",             inline=True)
    embed.add_field(name="🚫 Бан",       value="Найти и заблокировать участника.",         inline=True)
    embed.add_field(name="✅ Доверие",     value="Найти и дать полный доступ.",   inline=True)
    embed.add_field(name="⛔ Убрать доверие",   value="Снять доверие с участника.",          inline=True)
    embed.add_field(name="✔️ Разбан",   value="Снять блокировку с участника.",           inline=True)
    embed.add_field(name="🔁 Передать",  value="Передать владение другому.",   inline=True)
    embed.add_field(name="👑 Забрать",     value="Забрать брошенный канал.",       inline=True)
    embed.add_field(name="🗑️ Удалить",    value="Удалить канал навсегда.", inline=True)
    embed.set_footer(text="Все кнопки доступны только владельцу, кроме «Забрать».")
    return embed


# ──────────────COG───────────────────#
class VoicePanel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(VoicePanelView())

    @app_commands.command(name="panel", description="Отправить панель управления голосовым каналом.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def send_panel(self, interaction: discord.Interaction):
        await interaction.channel.send(embed=build_panel_embed(), view=VoicePanelView())
        await interaction.response.send_message("✅ Панель отправлена!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoicePanel(bot))
