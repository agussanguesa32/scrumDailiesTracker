import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging
import asyncio
from datetime import datetime
import pytz
from utils.config import config, dailies_storage, messages_storage

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DailiesBot')

class DailiesBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.dm_messages = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
    async def setup_hook(self):
        logger.info("Loading cogs...")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('_'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f"Loaded cog: {filename[:-3]}")
                except Exception as e:
                    logger.error(f"Failed to load cog {filename[:-3]}: {e}")

        await self.tree.sync()
        logger.info("Synced command tree")
    
    async def on_ready(self):
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Connected to {len(self.guilds)} guilds')

        # Registrar el view persistente
        try:
            from cogs.daily_scheduler import DailyReminderView
            view = DailyReminderView()
            self.add_view(view)
            logger.info("Registered persistent view")

            # Deshabilitar botones según regla al iniciar: pasado o ya completado
            try:
                tz = pytz.timezone(config.TIMEZONE)
                today_str = datetime.now(tz).strftime('%Y-%m-%d')
                all_data = await messages_storage.list_all()

                # Procesar fechas anteriores: deshabilitar todo
                for date_str, guilds_map in all_data.items():
                    is_past = date_str < today_str
                    for guild_id_str, users_map in guilds_map.items():
                        for user_id_str, entry in users_map.items():
                            should_disable = is_past
                            if not should_disable and date_str == today_str:
                                try:
                                    if config.GUILD_ID and int(guild_id_str) != int(config.GUILD_ID):
                                        pass
                                    else:
                                        already = await dailies_storage.has_submitted_today(int(user_id_str), int(guild_id_str))
                                        should_disable = already
                                except Exception:
                                    should_disable = False
                            if not should_disable:
                                continue

                            channel_id = int(entry.get('channel_id', 0))
                            message_id = int(entry.get('message_id', 0))
                            if not channel_id or not message_id:
                                continue

                            # Intentar obtener el canal por ID; fallback: abrir DM con el usuario
                            dm_channel = self.get_channel(channel_id)
                            if dm_channel is None:
                                try:
                                    dm_channel = await self.fetch_channel(channel_id)
                                except Exception:
                                    dm_channel = None
                            if dm_channel is None:
                                try:
                                    user = self.get_user(int(user_id_str)) or await self.fetch_user(int(user_id_str))
                                    dm_channel = user.dm_channel or await user.create_dm()
                                except Exception:
                                    dm_channel = None
                            if dm_channel is None:
                                continue

                            try:
                                msg = await dm_channel.fetch_message(message_id)
                            except Exception:
                                continue

                            try:
                                disabled_view = DailyReminderView()
                                for item in disabled_view.children:
                                    if isinstance(item, discord.ui.Button) and item.custom_id == "daily_complete_btn":
                                        item.disabled = True
                                await msg.edit(view=disabled_view)
                                await messages_storage.mark_disabled(int(user_id_str), int(guild_id_str), date_str)
                            except Exception:
                                pass

                logger.info("Persistent views checked and outdated/used buttons disabled where applicable")
            except Exception as e:
                logger.error(f"Error disabling persistent buttons on startup: {e}")
        except Exception as e:
            logger.error(f"Error registering persistent view: {e}")

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="las dailies del equipo"
        )
        await self.change_presence(activity=activity)

async def main():
    bot = DailiesBot()
    
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("No token found! Please set DISCORD_TOKEN in .env file")
        return
    
    try:
        await bot.start(token)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())