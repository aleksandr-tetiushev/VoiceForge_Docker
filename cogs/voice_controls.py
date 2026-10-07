import discord
from discord.ext import commands
from discord import app_commands
from cogs.voice_manager import VoiceManager
from typing import Optional
from config import * 
import asyncio
from . import databaseio as DB_SERVER_IO
from logger import log_error , log_info
import traceback
from . import database_channel_operations as DB_CHANNEL_IO

# all voice control commands
class VoiceControls(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    def is_guild(self,interaction: discord.Interaction) -> bool:
        return isinstance(interaction.guild, discord.Guild)
    
    def verify_ownership(self,interaction:discord.Interaction)-> bool: # verifying ownership 
        if not interaction.guild_id:
            return False
    
        if not self.user_in_voice_channel_check(interaction): # main command handles the user in voice but still to prevent crashes we check user's voice status
            return False

        channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

        if not isinstance(channel,DB_CHANNEL_IO.Channel):
            return False
        
        if interaction.user.id == channel.owner_id:
            return True
        
        return False

    def user_in_voice_channel_check(self,interaction:discord.Interaction) -> bool: # checks if user is in voice channel or not
        return bool(interaction.user.voice and interaction.user.voice.channel)
    
    def user_in_same_voice_channel(self, interaction: discord.Interaction, member: discord.Member) -> bool:
        return (member.voice and interaction.user.voice and member.voice.channel == interaction.user.voice.channel)
        
    async def send(self,interaction:discord.Interaction, msg:str , ephemeral:bool = True)-> None: # sends message or send followup if response is already sent
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(msg, ephemeral=ephemeral)

    async def send_embed(self,interaction:discord.Interaction, embed:discord.Embed , ephemeral:bool = True)-> None: # sends embed or send followup if response is already sent
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
 
    def get_voice_manager(self) -> Optional[VoiceManager]: # get VoiceManager cog
        return self.bot.get_cog("VoiceManager")
        
    # slash commands 
    @app_commands.command(name="rename", description="Переименовать голосовой канал (макс. 32 символа)")
    @app_commands.checks.cooldown(1, RENAME_COOLDOWN)
    async def rename(self, interaction: discord.Interaction, name: str):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере.")
                return
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return
            name = name.strip()
    
            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not name:
                await self.send(interaction=interaction,msg="❌ Название канала не может быть пустым.")
                return
            
            if len(name) > MAX_RENAME_CHARACTER_LIMIT:
                await self.send(interaction=interaction,msg=f"❌ Название канала не может быть длиннее {MAX_RENAME_CHARACTER_LIMIT} символов.")
                return
    
            channel = interaction.user.voice.channel 
            
            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            if channel.name == name:
                await self.send(interaction=interaction,msg="❌ У канала уже такое название.")
                return
            
            await channel.edit(name=name) #changing voice channel name
            await self.send(interaction=interaction,msg="✅ Голосовой канал успешно переименован.")
            return
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : rename - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
       
    @app_commands.command(name="claim", description="Забрать текущий голосовой канал")
    @app_commands.checks.cooldown(1, CLAIM_TRANSFER_COOLDOWN)
    async def claim(self,interaction:discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере.")
                return
            if not self.user_in_voice_channel_check(interaction): # checks if interaction happened in voice channel
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            db_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(db_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            owner_id = db_channel.owner_id

            if owner_id == interaction.user.id: # making sure the command isnt run by owner itself
                await self.send(interaction=interaction,msg="❌ Вы уже владелец этого голосового канала.")
                return

            owner = interaction.guild.get_member(owner_id) if owner_id else None 

            voice_channel = interaction.guild.get_channel(db_channel.channel_id)

            if not voice_channel or not owner:
                await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
                return 

            if owner in voice_channel.members: # checking if owner is in channel or not
                await self.send(interaction=interaction,msg="❌ Текущий владелец всё ещё в голосовом канале.")
                return

           
            edit_status = DB_CHANNEL_IO.channel_edit(server_id=voice_channel.guild.id,channel_id=voice_channel.id,new_owner_id=interaction.user.id)
            if not edit_status:
                await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
                return

            owner_overwrite = discord.PermissionOverwrite( # permission overwrites for voice channel owner 
                connect=True,
                read_message_history=True,
                speak=True,
                stream=True,
                use_voice_activation=True,
                view_channel=True,
                send_messages=True
            )

            overwrites = {
                interaction.user : owner_overwrite,
                self.bot.user: discord.PermissionOverwrite( # bot's permissions 
                    connect=True,
                    view_channel=True,
                    send_messages=True
                )
            }

            channel_edit = {
                'overwrites' : overwrites,
                'user_limit' : 0
            }

            if not voice_channel.name == f"🔥・костёр {interaction.user.display_name}": # renaming voice channel 
                channel_edit['name'] = f"🔥・костёр {interaction.user.display_name}"

            await voice_channel.edit(**channel_edit)

            await self.send(interaction=interaction,msg="✅ Теперь вы владелец этого голосового канала.")
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : claim - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
    
    @app_commands.command(name="limit", description="Изменить лимит участников канала (1–99) или 0, чтобы снять лимит")
    @app_commands.checks.cooldown(1,LIMIT_CHANGE_COOLDOWN)
    async def limit(self,interaction:discord.Interaction,limit:int):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not 0 <= limit <= 99: # making sure limit isnt more or less than limit by discord
                await self.send(interaction=interaction,msg="❌ Лимит должен быть от 1 до 99, либо 0, чтобы снять лимит.")
                return

            channel = interaction.user.voice.channel 

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return

            if channel.user_limit == limit: # avoiding unnecessary api calls 
               await self.send(interaction, "❌ У канала уже установлен такой лимит.")
               return

            if limit == 0: # vc limit reset
                await channel.edit(user_limit=0)
                await self.send(interaction=interaction,msg=f"✅ Лимит голосового канала снят.")
                return

            await channel.edit(user_limit=limit)
            await self.send(interaction=interaction,msg=f"✅ Лимит голосового канала установлен: `{limit}`.")
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : limit - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
        
    @app_commands.command(name="kick",description="Выгнать участников из вашего голосового канала (до 5 за раз)")
    @app_commands.checks.cooldown(1,KICK_MEMBER_COOLDOWN)
    async def kick(self,interaction:discord.Interaction,
                   member1: discord.Member,
                   member2: discord.Member|None=None,
                   member3: discord.Member|None=None,
                   member4: discord.Member|None=None,
                   member5: discord.Member|None=None):
        
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
            
            members:discord.Member = [member1,member2,member3,member4,member5]

            members:set[discord.Member] = set(members) # making sure there are no repeated users
            kicked_members = []
            for member in members:

                if not member:
                    continue
                
                if member.id == interaction.user.id:
                    continue
                
                if not self.user_in_same_voice_channel(interaction, member):
                    continue
                
                await member.move_to(None)

                kicked_members.append(member.mention)
                await asyncio.sleep(0.3)  # delay to avoid rate limit

            value = "\n".join(kicked_members) if kicked_members else "Никого не выгнали."

            embed = discord.Embed(
                title="Выгнанные участники",
                description="Эти участники были выгнаны из вашего голосового канала.",
                color=discord.Color.blurple()
            )

            embed.add_field(
                name="Выгнаны:",
                value=value,
                inline=False
            )

            embed.set_footer(
                text="Примечание: если указанного вами участника нет в списке выше, его не было в вашем канале или его не удалось отключить."
                )


            await self.send_embed(interaction=interaction,embed=embed)
            return
    
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : kick - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
            
    @app_commands.command(name="lock",description="Закрыть текущий голосовой канал")
    @app_commands.checks.cooldown(1,LOCK_AND_UNLOCK_COOLDOWN)
    async def lock(self,interaction:discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return

            channel = interaction.user.voice.channel 
            everyone = interaction.guild.default_role
            overwrite = channel.overwrites_for(everyone)

            if overwrite.connect is False: # verifying if voice channel isnt locked already to avoid unnecessary api calls
                await self.send(interaction, "Голосовой канал уже закрыт.")
                return        

            overwrite.connect = False
            await channel.set_permissions(everyone, overwrite=overwrite)
            await self.send(interaction, "🔒 Голосовой канал закрыт.")
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : lock - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
    
    @app_commands.command(name="unlock",description="Открыть текущий голосовой канал")
    @app_commands.checks.cooldown(1,LOCK_AND_UNLOCK_COOLDOWN)
    async def unlock(self,interaction:discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return

            channel = interaction.user.voice.channel 
            everyone = interaction.guild.default_role
            overwrite = channel.overwrites_for(everyone)

            if overwrite.connect is True: # verifying if voice channel isnt unlocked already to avoid unnecessary api calls
                await self.send(interaction, "Голосовой канал уже открыт.")
                return        

            overwrite.connect = True
            await channel.set_permissions(everyone, overwrite=overwrite)
            await self.send(interaction, "🔓 Голосовой канал открыт.")
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : unlock - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
    
    @app_commands.command(name="delete",description="Удалить текущий голосовой канал")
    @app_commands.checks.cooldown(1,DELETE_COOLDOWN) # cooldown in this command prevents user from using same command for 2 different voice channel withing small interval and prevents rate limitng
    async def delete(self,interaction:discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
        
            try:
                await interaction.channel.delete(reason=f"Использована команда удаления.")
                delete_status = DB_CHANNEL_IO.channel_delete(server_id=interaction.channel.guild.id,channel_id=interaction.channel_id)
            except discord.NotFound:
                delete_status = DB_CHANNEL_IO.channel_delete(server_id=interaction.channel.guild.id,channel_id=interaction.channel_id)
                await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
                return
            
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : delete - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
    
    @app_commands.command(name="invite",description="Отправить приглашение в ваш голосовой канал (до 5 за раз)")
    @app_commands.checks.cooldown(1,INVITE_COOLDOWN)
    async def invite(self, interaction: discord.Interaction,
                   member1: discord.Member,
                   member2: discord.Member|None=None,
                   member3: discord.Member|None=None,
                   member4: discord.Member|None=None,
                   member5: discord.Member|None=None):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
        
            members:set[discord.Member] = {member1,member2,member3,member4,member5}
            members.discard(None)
            channel = interaction.user.voice.channel

            guild = interaction.guild
            invite_link = f"https://discord.com/channels/{guild.id}/{channel.id}"

            invite_sent = []

            for member in members:
                if not member:
                    continue

                if member.bot:
                    continue

                try: 
                    if member.id == interaction.user.id:
                        continue
                    
                    if self.user_in_same_voice_channel(interaction, member):
                        continue
                    
                    await member.send(f"Вас пригласили в канал **{channel.name}**.\n"f"Нажмите, чтобы зайти: {invite_link}") 
                    invite_sent.append(member.mention)

                except discord.Forbidden:
                    pass

            embed = discord.Embed(color=discord.Color.blurple())

            value = "\n".join(invite_sent) if invite_sent else "Никого не пригласили."

            embed.add_field(
                name="✅ Приглашены:",
                value=value,
                inline=False
            )

            embed.set_footer(
                text="Примечание: если указанного вами участника нет в списке выше, бот не может пригласить его в этот канал."
            )

            await self.send_embed(interaction=interaction, embed=embed)
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : invite - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @app_commands.command(name="hide",description="Скрыть текущий голосовой канал от всех. Видеть его смогут только доверенные.")
    @app_commands.checks.cooldown(1, HIDE_UNHIDE_COOLDOWN)
    async def hide(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return

            channel = interaction.user.voice.channel
            everyone = interaction.guild.default_role

            if not channel.permissions_for(everyone).view_channel:
                await self.send(interaction, "❌ Этот голосовой канал уже скрыт.")
                return

            overwrite = channel.overwrites_for(everyone)
            overwrite.view_channel = False

            await channel.set_permissions(everyone, overwrite=overwrite)
            await self.send(interaction, "🚫 Голосовой канал скрыт.")

        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : hide - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @app_commands.command(name="unhide",description="Сделать текущий голосовой канал видимым для всех.")
    @app_commands.checks.cooldown(1, HIDE_UNHIDE_COOLDOWN)
    async def unhide(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return

            channel = interaction.user.voice.channel
            everyone = interaction.guild.default_role

            if channel.permissions_for(everyone).view_channel:
                await self.send(interaction, "❌ Этот голосовой канал уже виден.")
                return

            overwrite = channel.overwrites_for(everyone)
            overwrite.view_channel = None # restore default visibility according to server settings

            await channel.set_permissions(everyone, overwrite=overwrite)
            await self.send(interaction, "👁️ Голосовой канал теперь виден.")
            return
    
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : unhide - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @app_commands.command(name="trust",description="Дать выбранным участникам доступ, даже если канал закрыт или скрыт (до 5 за раз).")
    @app_commands.checks.cooldown(1, TRUST_UNTRUST_COOLDOWN)
    async def trust(self,interaction: discord.Interaction,
        member1: discord.Member,
        member2: discord.Member | None = None,
        member3: discord.Member | None = None,
        member4: discord.Member | None = None,
        member5: discord.Member | None = None
        ):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return

            channel = interaction.user.voice.channel
            overwrites = channel.overwrites

            members:set[discord.Member] = {member1, member2, member3, member4, member5}
            members.discard(None)
            trusted = []

            for member in members:

                if member.bot:
                    continue

                if member.id == interaction.user.id:
                    continue
                
                overwrite = overwrites.get(member, discord.PermissionOverwrite())
                if (overwrite.connect is True and 
                    overwrite.speak is True and 
                    overwrite.stream is True and 
                    overwrite.use_voice_activation is True and 
                    overwrite.view_channel is True
                    ): # preventing unnecessary overwrites
                     continue

                overwrite.view_channel = True
                overwrite.connect = True
                overwrite.stream = True
                overwrite.use_voice_activation = True
                overwrite.speak = True

                overwrites[member] = overwrite
                trusted.append(member.mention)

            view = "\n".join(trusted) if trusted else "Не указано ни одного подходящего участника."

            if trusted:
                await channel.edit(overwrites=overwrites)

            embed = discord.Embed(
                color=discord.Color.blurple()
                )

            embed.add_field(
                name="✅ Доверенные:",
                value=view,
                inline=False
            )
            embed.set_footer(text="Примечание: если указанного вами участника нет в списке выше, бот не может изменить его статус доверия в этом канале.")
            await self.send_embed(interaction=interaction,embed=embed)
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : trust - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
    
    @app_commands.command(name="trusted",description="Показать доверенных участников.")
    @app_commands.checks.cooldown(1,TRUSTED_BLOCKED_COOLDOWN)
    async def trusted(self,interaction:discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return

            channel = interaction.user.voice.channel
            trusted_members:list[discord.Member] = []

            for member , overwrite in channel.overwrites.items():
                if isinstance(member,discord.Member):
                    if member.id == interaction.user.id: # its not possible for owner of voice channel to be added as trusted but still checking it doesnt add owner in trusted member list
                        continue
                    
                    if (overwrite.connect is True and 
                        overwrite.speak is True and 
                        overwrite.stream is True and 
                        overwrite.use_voice_activation is True and 
                        overwrite.view_channel is True
                        ):

                        trusted_members.append(member)

            value = "\n".join(member.mention for member in trusted_members) if trusted_members else "Доверенных участников нет."

            embed = discord.Embed(
                title="Доверенные участники",
                description="Сейчас доверенные участники:",
                color=discord.Color.blurple()
                )

            embed.add_field(
                name="Сейчас доверены:",
                value=value,
                inline=False
            )

            await self.send_embed(interaction=interaction,embed=embed)
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : trusted - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
 
    @app_commands.command(name="untrust",description="Убрать выбранных участников из списка доверенных (до 5 за раз).")
    @app_commands.checks.cooldown(1,TRUST_UNTRUST_COOLDOWN)
    async def untrust(self,interaction:discord.Interaction,
            member1: discord.Member,
            member2: discord.Member | None = None,
            member3: discord.Member | None = None,
            member4: discord.Member | None = None,
            member5: discord.Member | None = None
            ):
        
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return

            channel = interaction.user.voice.channel
            overwrites = channel.overwrites

            members:set[discord.Member] = {member1, member2, member3, member4, member5}
            members.discard(None)
            untrusted = []

            for member in members:

                if member.id == interaction.user.id:
                    continue
                
                overwrite = overwrites.get(member, discord.PermissionOverwrite())
                if (overwrite.connect is not True and 
                        overwrite.speak is not True and 
                        overwrite.stream is not True and 
                        overwrite.use_voice_activation is not True and 
                        overwrite.view_channel is not True
                        ): # Skip users who are not currently trusted
                     continue
                 
                # Reset permissions to inherit from role defaults
                overwrite.view_channel = None
                overwrite.connect = None
                overwrite.stream = None
                overwrite.use_voice_activation = None
                overwrite.speak = None

                overwrites[member] = overwrite
                untrusted.append(member.mention)

            view = "\n".join(untrusted) if untrusted else "Не указано ни одного подходящего участника."

            if untrusted:
                await channel.edit(overwrites=overwrites)

            embed = discord.Embed(
                color=discord.Color.blurple()
                )

            embed.add_field(
                name="✅ Доверие снято:",
                value=view,
                inline=False
            )

            embed.set_footer(text="Примечание: если указанного вами участника нет в списке выше, бот не может изменить его статус доверия в этом канале.")
            await self.send_embed(interaction=interaction,embed=embed)
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : untrust - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
    
    @app_commands.command(name="block",description="Выгнать и заблокировать выбранных участников в канале (до 5 за раз).")
    @app_commands.checks.cooldown(1,BLOCK_UNBLOCK_COOLDOWN)
    async def block(self,interaction:discord.Interaction,
                    member1: discord.Member,
                    member2: discord.Member | None = None,
                    member3: discord.Member | None = None,
                    member4: discord.Member | None = None,
                    member5: discord.Member | None = None
                    ):
        
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return

            channel = interaction.user.voice.channel
            overwrites = channel.overwrites

            members:set[discord.Member] = {member1, member2, member3, member4, member5}
            members.discard(None)
            blocked = []

            for member in members:

                if member.bot:
                    continue

                if member.id == interaction.user.id:
                    continue

                overwrite = overwrites.get(member, discord.PermissionOverwrite())
                if overwrite.connect is False and overwrite.view_channel is False: # preventing unnecessary overwrites but setting it to false if any one of 2 required permissions is not False
                     continue
                 
                overwrite.view_channel = False # will not show channel to blocked user
                overwrite.connect = False # will not let blocked user to connect
                overwrites[member] = overwrite

                if member in channel.members: # kicking user from voice channel 
                    await member.move_to(None) 

                blocked.append(member.mention)

            view = "\n".join(blocked) if blocked else "Не указано ни одного подходящего участника."

            await channel.edit(overwrites=overwrites)
            embed = discord.Embed(
                color=discord.Color.blurple()
                )

            embed.add_field(
                name="✅ Заблокированы:",
                value=view,
                inline=False
            )

            embed.set_footer(text="Примечание: если указанного вами участника нет в списке выше, бот не может заблокировать или разблокировать его в этом канале.")
            await self.send_embed(interaction=interaction,embed=embed)
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : block - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @app_commands.command(name="blocked",description="Показать заблокированных участников.")
    @app_commands.checks.cooldown(1,TRUSTED_BLOCKED_COOLDOWN)
    async def blocked(self,interaction:discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return

            channel = interaction.user.voice.channel
            blocked_members:list[discord.Member] = []

            for member , overwrite in channel.overwrites.items():
                if isinstance(member,discord.Member):
                    if member.id == interaction.user.id: # owner should never appear in blocked list
                        continue
                    
                    if member.bot:
                        continue
                    
                    if overwrite.view_channel is False and overwrite.connect is False:
                        blocked_members.append(member)

            value = "\n".join(member.mention for member in blocked_members) if blocked_members else "Заблокированных участников нет."

            embed = discord.Embed(
                title="Заблокированные участники",
                description="Эти участники сейчас заблокированы в голосовом канале.",
                color=discord.Color.blurple()
                )

            embed.add_field(
                name="Сейчас заблокированы:",
                value=value,
                inline=False
            )

            await self.send_embed(interaction=interaction,embed=embed)
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : blocked - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
    
    @app_commands.command(name="unblock",description="Убрать выбранных участников из списка заблокированных (до 5 за раз).")
    @app_commands.checks.cooldown(1,BLOCK_UNBLOCK_COOLDOWN)
    async def unblock(self,interaction:discord.Interaction,
            member1: discord.Member,
            member2: discord.Member | None = None,
            member3: discord.Member | None = None,
            member4: discord.Member | None = None,
            member5: discord.Member | None = None
            ):
        
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return

            channel = interaction.user.voice.channel
            overwrites = channel.overwrites

            members:set[discord.Member] = {member1, member2, member3, member4, member5}
            members.discard(None)
            unblocked:list[discord.Member] = []

            for member in members:

                if member.bot:
                    continue

                if member.id == interaction.user.id:
                    continue
                
                overwrite = overwrites.get(member, discord.PermissionOverwrite())
                if overwrite.connect is not False and overwrite.view_channel is not False: # preventing unnecessary overwrites but reseting if any one of 2 required permissions are False
                     continue

                # Reset permissions to inherit from role defaults
                overwrite.view_channel = None
                overwrite.connect = None

                overwrites[member] = overwrite
                unblocked.append(member.mention)

            view = "\n".join(unblocked) if unblocked else "Не указано ни одного подходящего участника."

            await channel.edit(overwrites=overwrites)
            embed = discord.Embed(
                color=discord.Color.blurple()
                )

            embed.add_field(
                name="✅ Разблокированы:",
                value=view,
                inline=False
            )

            embed.set_footer(text="Примечание: если указанного вами участника нет в списке выше, бот не может заблокировать или разблокировать его в этом канале.")
            await self.send_embed(interaction=interaction,embed=embed)
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : unblock - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
    
    @app_commands.command(name="transfer",description="Передать ваш голосовой канал другому участнику канала.")
    @app_commands.checks.cooldown(1,CLAIM_TRANSFER_COOLDOWN)
    async def transfer(self,interaction:discord.Interaction,new_owner:discord.Member):
        try:
            await interaction.response.defer(ephemeral=True)
            if not self.is_guild(interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере")
                return
            
            if not self.user_in_voice_channel_check(interaction):
                await self.send(interaction=interaction,msg="❌ Для этого нужно находиться в голосовом канале.")
                return

            voice_channel = DB_CHANNEL_IO.channel_read(server_id=interaction.guild_id,channel_id=interaction.user.voice.channel.id)

            if not isinstance(voice_channel,DB_CHANNEL_IO.Channel):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только во временных голосовых каналах.")
                return

            if not self.verify_ownership(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Вы не владелец этого голосового канала.")
                return
        
            channel = interaction.user.voice.channel

            if new_owner.bot:
                await self.send(interaction,msg="❌ Некорректный пользователь.")
                return

            if interaction.user.id == new_owner.id:
                await self.send(interaction=interaction,msg="❌ Нельзя передать канал самому себе.")
                return

            if new_owner not in channel.members: # checking if new_owner is in channel or not
                await self.send(interaction=interaction,msg="❌ Выбранного пользователя нет в голосовом канале.")
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
                new_owner : owner_overwrite,
                self.bot.user: discord.PermissionOverwrite( # bot's permissions 
                    connect=True,
                    view_channel=True,
                    send_messages=True
                )
            }

            channel_edit = {
                'overwrites' : overwrites,
                'user_limit' : 0
            }

            if not channel.name == f"🔥・костёр {new_owner.display_name}": # renaming voice channel 
                channel_edit['name'] = f"🔥・костёр {new_owner.display_name}"

            await channel.edit(**channel_edit)
            edit_status = DB_CHANNEL_IO.channel_edit(server_id=interaction.guild_id,channel_id=channel.id,new_owner_id=new_owner.id)

            if not edit_status:
                log_error(message=f"Location : transfer - file : voice_controls.py - Error Name : edit_status error - description : reached till here because channel_read returned info but edit didnt worked")
                await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
                return
            
            await self.send(interaction=interaction,msg=f"✅ Владение голосовым каналом передано: {new_owner.mention}.")
            return
        
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : transfer - file : voice_controls.py : Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
    
    @app_commands.command(name="register",description="Назначить голосовой канал и его категорию для создания временных каналов.")
    async def register(self,interaction: discord.Interaction, channel: discord.VoiceChannel = None):
        try:
            if not self.is_guild(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере.")
                return
            
            await interaction.response.defer()
            
            if not interaction.user.guild_permissions.administrator: # fallback if user is not admin of server
                await self.send(interaction=interaction,msg=f"❌ Доступ запрещён: команда доступна только администраторам сервера.",ephemeral=False)
                return
            
            if not interaction.guild.me.guild_permissions.administrator: # fall back if bot dont have admin permission in server
                await self.send(interaction=interaction,msg=f"❌ У меня нет прав администратора. Выдайте моей роли права администратора, чтобы продолжить.",ephemeral=False)
                return
    
            if not channel or not isinstance(channel,discord.VoiceChannel):
                await self.send(interaction=interaction,msg=f"❌ Неверный канал. Укажите голосовой канал.",ephemeral=False)
                return
            
            if not channel.category: # fallback on no category
                await self.send(interaction=interaction,msg=f"❌ У этого канала нет категории. Укажите канал, находящийся в категории.",ephemeral=False)
                return
    
            server_object , read_status = DB_SERVER_IO.server_read(interaction=interaction)
    
            if read_status: # fallback on already registered
                await self.send(interaction=interaction,msg=f"❌ На этом сервере уже зарегистрирован канал-создатель. Сначала выполните `/unregister`.")
                return
            
            write_status = DB_SERVER_IO.server_write(channel=channel)
    
            if not write_status:
                await self.send(interaction=interaction,msg=f"❌ Не удалось зарегистрировать канал. Повторите попытку.",ephemeral=False)
                return
            
            voice_manager = self.get_voice_manager()
            if not isinstance(voice_manager,VoiceManager):
                DB_SERVER_IO.server_delete(interaction=interaction) # remove server entry
                await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.",ephemeral=False)
                return 

            voice_manager.creator_channels[channel.guild.id] = channel.id
            voice_manager.temp_channel_category[channel.guild.id] = channel.category.id # load current entry into voice_manager in-memory cache to start listening that channel also 
            await self.send(interaction=interaction,msg=f"✅ Канал успешно зарегистрирован.",ephemeral=False)
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : register - filename : voice_controls.py - Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return 
        
    @app_commands.command(name="unregister",description="Удалить зарегистрированный голосовой канал из настроек сервера.")
    async def unregister(self,interaction: discord.Interaction):
        try:
            if not self.is_guild(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере.")
                return
            await interaction.response.defer()
            
            if not interaction.user.guild_permissions.administrator: # fallback if user is not admin of server
                await self.send(interaction=interaction,msg=f"❌ Доступ запрещён: команда доступна только администраторам сервера.",ephemeral=False)
                return
            
            if not interaction.guild.me.guild_permissions.administrator: # fall back if bot dont have admin permission in server
                await self.send(interaction=interaction,msg=f"❌ У меня нет прав администратора. Выдайте моей роли права администратора, чтобы продолжить.",ephemeral=False)
                return
            
            server_object , read_status = DB_SERVER_IO.server_read(interaction=interaction)
    
            if not read_status: # fallback on no entry
                await self.send(interaction=interaction,msg=f"❌ На этом сервере нет зарегистрированного канала-создателя. Сначала выполните `/register`.")
                return
            
            write_status = DB_SERVER_IO.server_delete(interaction=interaction)
    
            if not write_status:
                await self.send(interaction=interaction,msg=f"❌ Не удалось удалить канал. Повторите попытку.",ephemeral=False)
                return
            
            voice_manager = self.get_voice_manager()
            if not isinstance(voice_manager,VoiceManager):
                await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.",ephemeral=False)
                return 
            
            voice_manager.temp_channel_category.pop(interaction.guild_id,None)
            voice_manager.creator_channels.pop(interaction.guild_id,None) # remove from in-memory cache
            await self.send(interaction=interaction,msg=f"✅ Регистрация канала снята. {self.bot.user.mention} продолжит отслеживать уже существующие временные каналы.",ephemeral=False)
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : unregister - filename : voice_controls.py - Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return

    @app_commands.command(name="setup",description="Показать инструкцию по настройке бота на сервере.")
    async def server_setup(self,interaction:discord.Interaction):
        try:
            if not self.is_guild(interaction=interaction):
                await self.send(interaction=interaction,msg=f"❌ Эта команда работает только на сервере.")
                return
            await interaction.response.defer()
            
            if not interaction.user.guild_permissions.administrator: # fallback if user is not admin of server
                await self.send(interaction=interaction,msg=f"❌ Доступ запрещён: команда доступна только администраторам сервера.",ephemeral=False)
                return
            
            if not interaction.guild.me.guild_permissions.administrator: # fall back if bot dont have admin permission in server
                await self.send(interaction=interaction,msg=f"❌ У меня нет прав администратора. Выдайте моей роли права администратора, чтобы продолжить.",ephemeral=False)
                return
            embed = discord.Embed(
                title=f"Спасибо, что выбрали {self.bot.user.name}!",
                description="Чтобы настроить бота на сервере, используйте команду:",
                color=discord.Color.blurple()
                )

            embed.add_field(
                name="`/register` <голосовой канал>",
                value=" Примечание: у голосового канала должна быть категория с обычными правами для @everyone, иначе бот не будет работать правильно.",
                inline=False
            )

            embed.set_footer(text="Если при использовании /register возникла ошибка, один раз выполните /unregister.")

            await self.send_embed(interaction=interaction,embed=embed,ephemeral=False)
            return
        except Exception as e:
            exception_traceback = traceback.format_exc()
            error_name = type(e).__name__
            log_error(message=f"Location : bot_setup - filename : voice_controls.py - Error Name - {error_name}",exc_info=exception_traceback)
            await self.send(interaction=interaction,msg=f"❌ Внутренняя ошибка. Повторите попытку или свяжитесь с разработчиками.")
            return
# Setup function to load the cog
async def setup(bot:commands.Bot):
    await bot.add_cog(VoiceControls(bot))
