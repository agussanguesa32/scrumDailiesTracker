import discord
from discord.ext import commands, tasks
import logging
from datetime import datetime, time
import pytz
import asyncio
from utils.config import config, schedule_manager, dailies_storage

logger = logging.getLogger('DailiesBot.Scheduler')

async def send_daily_reminders(bot, guild):
    sent_count = 0

    # Enviar mensaje al canal de dailies con la fecha
    channel = guild.get_channel(config.DAILIES_CHANNEL_ID)
    if channel:
        try:
            tz = pytz.timezone(config.TIMEZONE)
            now = datetime.now(tz)

            # Días de la semana en español
            dias_semana = {
                'Monday': 'Lunes',
                'Tuesday': 'Martes',
                'Wednesday': 'Miércoles',
                'Thursday': 'Jueves',
                'Friday': 'Viernes',
                'Saturday': 'Sábado',
                'Sunday': 'Domingo'
            }

            dia_español = dias_semana[now.strftime('%A')]
            fecha_formateada = now.strftime('%d/%m/%Y')

            fecha_mensaje = f"# Dailies del día\n# {dia_español} - {fecha_formateada}"
            await channel.send(fecha_mensaje)
            logger.info(f"Sent daily date message to channel in {guild.name}")
        except Exception as e:
            logger.error(f"Error sending date message to channel: {e}")

    for role_id in config.PRODUCT_TEAM_ROLES:
        role = guild.get_role(role_id)
        if not role:
            logger.warning(f"Role {role_id} not found in guild {guild.name}")
            continue
        
        for member in role.members:
            if member.bot:
                continue
            
            already_submitted = await dailies_storage.has_submitted_today(member.id, guild.id)
            if already_submitted:
                logger.info(f"User {member.name} already submitted daily today")
                continue
            
            try:
                tz = pytz.timezone(config.TIMEZONE)
                now = datetime.now(tz)

                # Días de la semana en español
                dias_semana = {
                    'Monday': 'Lunes',
                    'Tuesday': 'Martes',
                    'Wednesday': 'Miércoles',
                    'Thursday': 'Jueves',
                    'Friday': 'Viernes',
                    'Saturday': 'Sábado',
                    'Sunday': 'Domingo'
                }

                dia_español = dias_semana[now.strftime('%A')]
                fecha_formateada = now.strftime('%d/%m/%Y')

                # Mensaje con fecha y día
                fecha_mensaje = f"# {dia_español} - {fecha_formateada}"
                await member.send(fecha_mensaje)

                embed = discord.Embed(
                    title="✨ ¡Buenos días!",
                    description="Completa tu daily clickeando en el botón de abajo.",
                    color=discord.Color.blue(),
                    timestamp=now
                )
                embed.set_footer(text="Daily")

                view = DailyReminderView()

                await member.send(embed=embed, view=view)
                sent_count += 1
                logger.info(f"Sent daily reminder to {member.name}")
                
                await asyncio.sleep(0.5)
                
            except discord.Forbidden:
                logger.warning(f"Cannot send DM to {member.name} - DMs disabled")
            except Exception as e:
                logger.error(f"Error sending DM to {member.name}: {e}")
    
    return sent_count

class DailyReminderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Sin timeout para persistencia

    @discord.ui.button(label="Completar Daily", style=discord.ButtonStyle.primary, emoji="📝", custom_id="daily_complete_btn")
    async def complete_daily(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = config.GUILD_ID

        # Verificar si ya completó la daily
        already_submitted = await dailies_storage.has_submitted_today(interaction.user.id, guild_id)
        if already_submitted:
            await interaction.response.send_message(
                "✅ Ya completaste tu daily de hoy. ¡Vuelve mañana!",
                ephemeral=True
            )
            return

        modal = DailyModal(guild_id=guild_id)
        await interaction.response.send_modal(modal)

class DailyModal(discord.ui.Modal, title="Daily"):
    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id
    
    feeling = discord.ui.TextInput(
        label="¿Cómo te sentís hoy? ✨ ¿Dormiste bien? 😴",
        placeholder="Ej: Me siento bien, dormí 8 horas",
        style=discord.TextStyle.short,
        required=True,
        max_length=200
    )
    
    yesterday = discord.ui.TextInput(
        label="¿Qué hiciste ayer? ¿Moviste alguna card?",
        placeholder="Ej: Completé la feature X, moví la card #123 a review",
        style=discord.TextStyle.long,
        required=True,
        max_length=500
    )
    
    today = discord.ui.TextInput(
        label="¿Qué vas a hacer hoy?",
        placeholder="Ej: Voy a trabajar en la feature Y, revisar PRs",
        style=discord.TextStyle.long,
        required=True,
        max_length=500
    )
    
    blockers = discord.ui.TextInput(
        label="¿Necesitás ayuda con algo? ¿Bloqueos? ¿PRs?",
        placeholder="Ej: Necesito review del PR #456, bloqueado por...",
        style=discord.TextStyle.long,
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        bot = interaction.client
        guild = bot.get_guild(self.guild_id)
        
        if not guild:
            await interaction.followup.send("❌ No se pudo encontrar el servidor.", ephemeral=True)
            return
        
        channel = guild.get_channel(config.DAILIES_CHANNEL_ID)
        if not channel:
            await interaction.followup.send("❌ No se pudo encontrar el canal de dailies.", ephemeral=True)
            return
        
        member = guild.get_member(interaction.user.id)
        if not member:
            await interaction.followup.send("❌ No se pudo encontrar tu usuario en el servidor.", ephemeral=True)
            return
        
        # Verificar primero si ya envió daily hoy
        already_submitted = await dailies_storage.has_submitted_today(interaction.user.id, self.guild_id)
        if already_submitted:
            await interaction.followup.send(
                "✅ Ya completaste tu daily de hoy. ¡Vuelve mañana!",
                ephemeral=True
            )
            return
        
        daily_data = {
            'feeling': self.feeling.value,
            'yesterday': self.yesterday.value,
            'today': self.today.value,
            'blockers': self.blockers.value or "Sin bloqueos"
        }
        
        # Intentar guardar la daily
        saved = await dailies_storage.save_daily(interaction.user.id, self.guild_id, daily_data)

        if not saved:
            # Si no se pudo guardar, probablemente ya existe
            await interaction.followup.send(
                "✅ Ya completaste tu daily de hoy. ¡Vuelve mañana!",
                ephemeral=True
            )
            return

        
        embed = discord.Embed(
            title=f"📋 Daily - {member.display_name}",
            color=discord.Color.green(),
            timestamp=datetime.now(pytz.timezone(config.TIMEZONE))
        )
        
        embed.set_author(
            name=str(member),
            icon_url=member.display_avatar.url if member.display_avatar else None
        )
        
        embed.add_field(
            name="✨ ¿Cómo te sentís hoy? / ¿Dormiste bien? 😴",
            value=self.feeling.value,
            inline=False
        )
        
        embed.add_field(
            name="📝 ¿Qué hiciste ayer?",
            value=self.yesterday.value,
            inline=False
        )
        
        embed.add_field(
            name="🎯 ¿Qué vas a hacer hoy?",
            value=self.today.value,
            inline=False
        )
        
        blockers_value = self.blockers.value or "Sin bloqueos"
        has_blockers = bool(self.blockers.value and self.blockers.value.strip())
        
        embed.add_field(
            name="🚧 Bloqueos / Ayuda necesaria" if has_blockers else "✅ Bloqueos",
            value=blockers_value,
            inline=False
        )
        
        if has_blockers:
            embed.color = discord.Color.orange()
        
        embed.set_footer(text=f"Daily #{await self._get_daily_number(member.id)}")
        
        try:
            await channel.send(embed=embed)
            
            success_embed = discord.Embed(
                title="✅ Daily enviada",
                description="Tu daily ha sido enviada exitosamente al canal del equipo.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error sending daily to channel: {e}")
            await interaction.followup.send(
                "❌ Hubo un error al enviar tu daily. Por favor, intenta de nuevo.",
                ephemeral=True
            )
    
    async def _get_daily_number(self, user_id: int) -> int:
        return 1

class DailyScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_task.start()
        self.reminder_task.start()
        self.end_of_day_task.start()
        self.last_run = None
        self.last_reminder = None
        self.last_end_of_day = None
    
    def cog_unload(self):
        self.daily_task.cancel()
        self.reminder_task.cancel()
        self.end_of_day_task.cancel()
    
    @tasks.loop(minutes=1)
    async def daily_task(self):
        try:
            schedule = await schedule_manager.load_schedule()
            
            if not schedule['enabled']:
                return
            
            tz = pytz.timezone(config.TIMEZONE)
            now = datetime.now(tz)
            
            current_day = now.strftime('%A').lower()
            if current_day not in schedule['days']:
                return
            
            scheduled_time = time(schedule['hour'], schedule['minute'])
            current_time = now.time()
            
            if (current_time.hour == scheduled_time.hour and 
                current_time.minute == scheduled_time.minute):
                
                today_str = now.strftime('%Y-%m-%d %H:%M')
                if self.last_run == today_str:
                    return
                
                self.last_run = today_str
                
                logger.info(f"Running daily task at {today_str}")
                
                for guild in self.bot.guilds:
                    sent_count = await send_daily_reminders(self.bot, guild)
                    logger.info(f"Sent {sent_count} daily reminders in {guild.name}")
                
        except Exception as e:
            logger.error(f"Error in daily task: {e}")
    
    @daily_task.before_loop
    async def before_daily_task(self):
        await self.bot.wait_until_ready()
        logger.info("Daily scheduler started")
    
    @tasks.loop(minutes=1)
    async def reminder_task(self):
        try:
            schedule = await schedule_manager.load_schedule()
            
            if not schedule.get('reminder_enabled', False):
                return
            
            tz = pytz.timezone(config.TIMEZONE)
            now = datetime.now(tz)
            
            current_day = now.strftime('%A').lower()
            if current_day not in schedule['days']:
                return
            
            reminder_hour = schedule.get('reminder_hour', 14)
            reminder_minute = schedule.get('reminder_minute', 0)
            
            scheduled_time = time(reminder_hour, reminder_minute)
            current_time = now.time()
            
            if (current_time.hour == scheduled_time.hour and 
                current_time.minute == scheduled_time.minute):
                
                today_str = now.strftime('%Y-%m-%d %H:%M')
                if self.last_reminder == today_str:
                    return
                
                self.last_reminder = today_str
                
                logger.info(f"Running reminder task at {today_str}")
                
                for guild in self.bot.guilds:
                    sent_count = await self.send_reminders(guild)
                    logger.info(f"Sent {sent_count} reminder messages in {guild.name}")
                
        except Exception as e:
            logger.error(f"Error in reminder task: {e}")
    
    async def send_reminders(self, guild):
        sent_count = 0
        today_dailies = await dailies_storage.get_today_dailies(guild.id)
        
        for role_id in config.PRODUCT_TEAM_ROLES:
            role = guild.get_role(role_id)
            if not role:
                continue
            
            for member in role.members:
                if member.bot or str(member.id) in today_dailies:
                    continue
                
                try:
                    embed = discord.Embed(
                        title="🔔 Recordatorio de Daily",
                        description="¡No te olvides de completar tu daily!",
                        color=discord.Color.orange(),
                        timestamp=datetime.now(pytz.timezone(config.TIMEZONE))
                    )
                    
                    await member.send(embed=embed)
                    sent_count += 1
                    logger.info(f"Sent reminder to {member.name}")
                    
                    await asyncio.sleep(0.5)
                    
                except discord.Forbidden:
                    logger.warning(f"Cannot send reminder to {member.name} - DMs disabled")
                except Exception as e:
                    logger.error(f"Error sending reminder to {member.name}: {e}")
        
        return sent_count
    
    @reminder_task.before_loop
    async def before_reminder_task(self):
        await self.bot.wait_until_ready()
        logger.info("Reminder scheduler started")

    async def send_end_of_day_summary(self, guild):
        today_dailies = await dailies_storage.get_today_dailies(guild.id)
        missing_users = []

        for role_id in config.PRODUCT_TEAM_ROLES:
            role = guild.get_role(role_id)
            if not role:
                continue

            for member in role.members:
                if member.bot:
                    continue

                if str(member.id) not in today_dailies:
                    missing_users.append(member)

        if not missing_users:
            return

        channel = guild.get_channel(config.DAILIES_CHANNEL_ID)
        if not channel:
            logger.error(f"Dailies channel not found in guild {guild.name}")
            return

        embed = discord.Embed(
            title="📊 Resumen del día",
            description="Los siguientes miembros del equipo no completaron su daily hoy:",
            color=discord.Color.red(),
            timestamp=datetime.now(pytz.timezone(config.TIMEZONE))
        )

        missing_mentions = " ".join([member.mention for member in missing_users])
        embed.add_field(
            name="❌ Dailies faltantes",
            value=missing_mentions,
            inline=False
        )

        embed.set_footer(text="Recordá completar tu daily mañana por favor!")

        try:
            await channel.send(embed=embed)
            logger.info(f"Sent end of day summary for {len(missing_users)} missing dailies")
        except Exception as e:
            logger.error(f"Error sending end of day summary: {e}")

    @tasks.loop(minutes=1)
    async def end_of_day_task(self):
        try:
            schedule = await schedule_manager.load_schedule()

            if not schedule['enabled']:
                return

            tz = pytz.timezone(config.TIMEZONE)
            now = datetime.now(tz)

            current_day = now.strftime('%A').lower()
            if current_day not in schedule['days']:
                return

            if now.hour == 23 and now.minute == 59:
                today_str = now.strftime('%Y-%m-%d %H:%M')
                if self.last_end_of_day == today_str:
                    return

                self.last_end_of_day = today_str

                logger.info(f"Running end of day task at {today_str}")

                for guild in self.bot.guilds:
                    await self.send_end_of_day_summary(guild)

                # Limpiar el archivo de dailies al final del día
                cleared = await dailies_storage.clear_all_dailies()
                if cleared:
                    logger.info("Dailies file cleared successfully at end of day")
                else:
                    logger.error("Failed to clear dailies file at end of day")


        except Exception as e:
            logger.error(f"Error in end of day task: {e}")

    @end_of_day_task.before_loop
    async def before_end_of_day_task(self):
        await self.bot.wait_until_ready()
        logger.info("End of day scheduler started")

async def setup(bot):
    await bot.add_cog(DailyScheduler(bot))