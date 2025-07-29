# Primary bot file. RUN THIS FILE TO START THE BOT

import os
import discord
from discord import Intents
from discord.ext import commands
from dotenv import load_dotenv

import pymysql as mariadb

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

FURRYVILLE_ID = os.getenv('FURRYVILLE_ID')
BTG_ID = os.getenv('BTG_ID')

intents = Intents.default()
intents.message_content = False

class FviClient(commands.Bot):
    def __init__(self,):
        super().__init__(command_prefix='!', intents=intents)
    
    async def setup_hook(self):
        # Initialize the database connection
        # print("🔗 Intializing DB connection...")
        # try:
        #     mariadb.init()
        # except Exception as e:
        #     print(f"Error initializing database connection: {e}")
        #     return
        # Load cogs
        print("🔧 Loading cogs...")
        await self.load_extension('cogs.maintenance')
        await self.load_extension('cogs.entry_get')
        await self.load_extension('cogs.entry_create')
        await self.load_extension('cogs.entry_edit')
        # await self.load_extension('cogs.test')

        guild_ids = [
            BTG_ID,
            FURRYVILLE_ID
        ]
        
        for guild_id in guild_ids:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"🔧 Slash commands synced to guild {guild_id}.")

        print("✅ Finished syncing to all guilds.")
        print("✅ Finished loading cogs.")

if __name__ == "__main__":
    bot = FviClient()
    bot.run(TOKEN)