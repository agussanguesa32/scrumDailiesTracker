import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
import pytz
from utils.config import config, dailies_storage
from cogs.daily_scheduler import DailyModal

logger = logging.getLogger('DailiesBot.Commands')

class DailyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="daily", description="Completar tu daily manualmente")
    async def daily(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Este comando solo puede ser usado en un servidor.",
                ephemeral=True
            )
            return
        
        has_role = any(
            role.id in config.PRODUCT_TEAM_ROLES 
            for role in interaction.user.roles
        )
        
        if not has_role:
            await interaction.response.send_message(
                "❌ No tienes permisos para usar este comando. Necesitas ser parte del equipo de producto.",
                ephemeral=True
            )
            return
        
        already_submitted = await dailies_storage.has_submitted_today(
            interaction.user.id, 
            interaction.guild.id
        )
        
        if already_submitted:
            await interaction.response.send_message(
                "✅ Ya completaste tu daily de hoy. ¡Vuelve mañana!",
                ephemeral=True
            )
            return
        
        modal = DailyModal(guild_id=interaction.guild.id)
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="daily_status", description="Ver quién ha completado su daily hoy")
    async def daily_status(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Este comando solo puede ser usado en un servidor.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        today_dailies = await dailies_storage.get_today_dailies(interaction.guild.id)
        
        completed_users = []
        pending_users = []
        
        for role_id in config.PRODUCT_TEAM_ROLES:
            role = interaction.guild.get_role(role_id)
            if not role:
                continue
            
            for member in role.members:
                if member.bot:
                    continue
                
                if str(member.id) in today_dailies:
                    completed_users.append(member.mention)
                else:
                    pending_users.append(member.mention)
        
        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.now(tz)
        
        embed = discord.Embed(
            title=f"📊 Estado de Dailies - {now.strftime('%d/%m/%Y')}",
            color=discord.Color.blue(),
            timestamp=now
        )
        
        if completed_users:
            embed.add_field(
                name=f"✅ Completadas ({len(completed_users)})",
                value="\n".join(completed_users[:10]) + (f"\n... y {len(completed_users)-10} más" if len(completed_users) > 10 else ""),
                inline=False
            )
        
        if pending_users:
            embed.add_field(
                name=f"⏳ Pendientes ({len(pending_users)})",
                value="\n".join(pending_users[:10]) + (f"\n... y {len(pending_users)-10} más" if len(pending_users) > 10 else ""),
                inline=False
            )
        
        completion_rate = len(completed_users) / (len(completed_users) + len(pending_users)) * 100 if (completed_users or pending_users) else 0
        
        embed.add_field(
            name="📈 Tasa de completación",
            value=f"{completion_rate:.1f}%",
            inline=False
        )
        
        embed.set_footer(text="Daily Tracker")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="daily_reminder", description="Enviar recordatorio manual a quienes no completaron su daily")
    async def daily_reminder(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Este comando solo puede ser usado en un servidor.",
                ephemeral=True
            )
            return
        
        admin_role_id = config.ADMIN_ROLE_ID
        if not any(role.id == admin_role_id for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Solo los administradores pueden enviar recordatorios manuales.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        today_dailies = await dailies_storage.get_today_dailies(interaction.guild.id)
        reminded_count = 0
        
        for role_id in config.PRODUCT_TEAM_ROLES:
            role = interaction.guild.get_role(role_id)
            if not role:
                continue
            
            for member in role.members:
                if member.bot or str(member.id) in today_dailies:
                    continue
                
                try:
                    embed = discord.Embed(
                        title="⏰ Recordatorio de Daily",
                        description="¡No olvides completar tu daily de hoy!",
                        color=discord.Color.orange()
                    )
                    
                    embed.add_field(
                        name="Cómo completarla",
                        value="Usa el comando `/daily` en el servidor o espera el mensaje automático.",
                        inline=False
                    )
                    
                    await member.send(embed=embed)
                    reminded_count += 1
                    
                except discord.Forbidden:
                    logger.warning(f"Cannot send reminder to {member.name}")
                except Exception as e:
                    logger.error(f"Error sending reminder to {member.name}: {e}")
        
        await interaction.followup.send(
            f"✅ Se enviaron {reminded_count} recordatorios.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(DailyCommands(bot))