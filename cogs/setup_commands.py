import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Optional
import logging
from utils.config import config, schedule_manager, format_days_spanish

logger = logging.getLogger('DailiesBot.Setup')

class SetupCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def is_admin(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        admin_role_id = config.ADMIN_ROLE_ID
        return any(role.id == admin_role_id for role in interaction.user.roles)
    
    @app_commands.command(name="setup", description="Configurar el bot de dailies")
    @app_commands.check(is_admin)
    async def setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚙️ Configuración de Dailies Bot",
            description="Usa los botones para configurar el bot",
            color=discord.Color.blue()
        )
        
        schedule = await schedule_manager.load_schedule()
        
        days_str = format_days_spanish(schedule['days'])
        status = "✅ Activado" if schedule['enabled'] else "❌ Desactivado"
        
        embed.add_field(
            name="Estado actual",
            value=status,
            inline=False
        )
        embed.add_field(
            name="Días activos",
            value=days_str,
            inline=False
        )
        embed.add_field(
            name="Hora de envío",
            value=f"{schedule['hour']:02d}:{schedule['minute']:02d} (Buenos Aires)",
            inline=False
        )
        
        reminder_status = "✅ Activado" if schedule.get('reminder_enabled', False) else "❌ Desactivado"
        reminder_time = f"{schedule.get('reminder_hour', 14):02d}:{schedule.get('reminder_minute', 0):02d}"
        embed.add_field(
            name="Recordatorio",
            value=f"{reminder_status} - {reminder_time}",
            inline=False
        )
        
        view = SetupView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="test_daily", description="Enviar una daily de prueba (solo admins)")
    @app_commands.check(is_admin)
    async def test_daily(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        from cogs.daily_scheduler import send_daily_reminders
        
        sent_count = await send_daily_reminders(self.bot, interaction.guild)
        
        embed = discord.Embed(
            title="📧 Test de Daily",
            description=f"Se enviaron {sent_count} mensajes de prueba a los miembros con los roles configurados.",
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    
    @setup.error
    @test_daily.error
    async def command_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "❌ No tienes permisos para usar este comando. Necesitas el rol de admin configurado.",
                ephemeral=True
            )
        else:
            logger.error(f"Error in command: {error}")
            await interaction.response.send_message(
                "❌ Ocurrió un error al ejecutar el comando.",
                ephemeral=True
            )

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="Configurar días", style=discord.ButtonStyle.primary, emoji="📅")
    async def configure_days(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DaysSelectView()

        # Configurar las opciones del select
        options = await view.create_options()
        view.select_days.options = options

        embed = discord.Embed(
            title="📅 Seleccionar días",
            description="Seleccioná los días en que querés que se envíen las dailies:\n\n✅ = Día actualmente activo\n📅 = Día inactivo",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Configurar hora", style=discord.ButtonStyle.primary, emoji="⏰")
    async def configure_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TimeConfigModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Horario recordatorio", style=discord.ButtonStyle.primary, emoji="🔔")
    async def configure_reminder(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ReminderConfigModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Activar/Desactivar", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def toggle_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        schedule = await schedule_manager.load_schedule()
        new_status = not schedule['enabled']
        await schedule_manager.toggle_enabled(new_status)
        
        status_text = "activado" if new_status else "desactivado"
        embed = discord.Embed(
            title="✅ Estado actualizado",
            description=f"El bot de dailies ha sido {status_text}",
            color=discord.Color.green() if new_status else discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Ver configuración", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def view_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        schedule = await schedule_manager.load_schedule()
        
        embed = discord.Embed(
            title="📋 Configuración actual",
            color=discord.Color.blue()
        )
        
        days_str = format_days_spanish(schedule['days'])
        status = "✅ Activado" if schedule['enabled'] else "❌ Desactivado"
        
        embed.add_field(name="Estado", value=status, inline=False)
        embed.add_field(name="Días", value=days_str, inline=False)
        embed.add_field(name="Hora", value=f"{schedule['hour']:02d}:{schedule['minute']:02d}", inline=False)
        
        reminder_status = "✅ Activado" if schedule.get('reminder_enabled', False) else "❌ Desactivado"
        reminder_time = f"{schedule.get('reminder_hour', 14):02d}:{schedule.get('reminder_minute', 0):02d}"
        embed.add_field(name="Recordatorio", value=f"{reminder_status} - {reminder_time}", inline=False)
        
        embed.add_field(name="Canal de dailies", value=f"<#{config.DAILIES_CHANNEL_ID}>", inline=False)
        
        roles_str = ", ".join([f"<@&{role_id}>" for role_id in config.PRODUCT_TEAM_ROLES])
        embed.add_field(name="Roles del equipo", value=roles_str or "No configurados", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class DaysSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    async def create_options(self):
        """Crea las opciones del select con los días actuales marcados"""
        schedule = await schedule_manager.load_schedule()
        current_days = schedule.get('days', [])

        options = [
            discord.SelectOption(
                label="Lunes",
                value="monday",
                emoji="✅" if "monday" in current_days else "📅",
                default="monday" in current_days
            ),
            discord.SelectOption(
                label="Martes",
                value="tuesday",
                emoji="✅" if "tuesday" in current_days else "📅",
                default="tuesday" in current_days
            ),
            discord.SelectOption(
                label="Miércoles",
                value="wednesday",
                emoji="✅" if "wednesday" in current_days else "📅",
                default="wednesday" in current_days
            ),
            discord.SelectOption(
                label="Jueves",
                value="thursday",
                emoji="✅" if "thursday" in current_days else "📅",
                default="thursday" in current_days
            ),
            discord.SelectOption(
                label="Viernes",
                value="friday",
                emoji="✅" if "friday" in current_days else "📅",
                default="friday" in current_days
            ),
            discord.SelectOption(
                label="Sábado",
                value="saturday",
                emoji="✅" if "saturday" in current_days else "📅",
                default="saturday" in current_days
            ),
            discord.SelectOption(
                label="Domingo",
                value="sunday",
                emoji="✅" if "sunday" in current_days else "📅",
                default="sunday" in current_days
            ),
        ]
        return options

    @discord.ui.select(
        placeholder="Seleccioná los días...",
        min_values=1,
        max_values=7
    )
    async def select_days(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_days = select.values

        await schedule_manager.update_days(selected_days)

        days_str = format_days_spanish(selected_days)

        embed = discord.Embed(
            title="✅ Días configurados",
            description=f"Los días activos ahora son: **{days_str}**",
            color=discord.Color.green()
        )

        embed.add_field(
            name="ℹ️ Información",
            value=f"Se enviarán dailies automáticamente los: {days_str}",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

class TimeConfigModal(discord.ui.Modal, title="Configurar hora de dailies"):
    hour_input = discord.ui.TextInput(
        label="Hora (0-23)",
        placeholder="10",
        style=discord.TextStyle.short,
        required=True,
        max_length=2
    )
    
    minute_input = discord.ui.TextInput(
        label="Minutos (0-59)",
        placeholder="0",
        style=discord.TextStyle.short,
        required=True,
        max_length=2
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            hour = int(self.hour_input.value)
            minute = int(self.minute_input.value)
            
            if not (0 <= hour <= 23):
                raise ValueError("Hora debe estar entre 0 y 23")
            if not (0 <= minute <= 59):
                raise ValueError("Minutos deben estar entre 0 y 59")
            
            await schedule_manager.update_time(hour, minute)
            
            embed = discord.Embed(
                title="✅ Hora configurada",
                description=f"La hora de envío ahora es: {hour:02d}:{minute:02d} (Buenos Aires)",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )

class ReminderConfigModal(discord.ui.Modal, title="Configurar recordatorio"):
    hour_input = discord.ui.TextInput(
        label="Hora del recordatorio (0-23)",
        placeholder="14",
        style=discord.TextStyle.short,
        required=True,
        max_length=2
    )
    
    minute_input = discord.ui.TextInput(
        label="Minutos (0-59)",
        placeholder="0",
        style=discord.TextStyle.short,
        required=True,
        max_length=2
    )
    
    enabled_input = discord.ui.TextInput(
        label="Activar recordatorio? (si/no)",
        placeholder="si",
        style=discord.TextStyle.short,
        required=True,
        max_length=2
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            hour = int(self.hour_input.value)
            minute = int(self.minute_input.value)
            enabled = self.enabled_input.value.lower() in ['si', 'sí', 's', 'yes', 'y']
            
            if not (0 <= hour <= 23):
                raise ValueError("Hora debe estar entre 0 y 23")
            if not (0 <= minute <= 59):
                raise ValueError("Minutos deben estar entre 0 y 59")
            
            # Validar que el recordatorio sea posterior a la hora de envío
            schedule = await schedule_manager.load_schedule()
            daily_time_minutes = schedule['hour'] * 60 + schedule['minute']
            reminder_time_minutes = hour * 60 + minute
            
            if reminder_time_minutes <= daily_time_minutes:
                raise ValueError(f"El recordatorio debe ser posterior a la hora de envío ({schedule['hour']:02d}:{schedule['minute']:02d})")
            
            await schedule_manager.update_reminder(enabled, hour, minute)
            
            status_text = "activado" if enabled else "desactivado"
            embed = discord.Embed(
                title="✅ Recordatorio configurado",
                description=f"Recordatorio {status_text} para las {hour:02d}:{minute:02d} (Buenos Aires)",
                color=discord.Color.green()
            )
            
            if enabled:
                embed.add_field(
                    name="ℹ️ Información",
                    value=f"Se enviará un recordatorio a quienes no hayan completado su daily a las {hour:02d}:{minute:02d}",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(SetupCommands(bot))