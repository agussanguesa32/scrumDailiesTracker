import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging
import asyncio

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