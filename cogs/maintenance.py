import asyncio
import os
import time
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

OWNER_ID = int(os.getenv("POSTMAN_ID"))  # Get owner ID from .env

class MaintenanceView(discord.ui.View):
    def __init__(self, cog, message: discord.Message):
        super().__init__(timeout=60)
        self.cog = cog
        self.message = message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ You are not authorized to use this panel.", ephemeral=True)
            return False
        return True

    def get_uptime_string(self) -> str:
        uptime_seconds = int(time.time() - self.cog.start_time)

        if uptime_seconds < 60:
            return "Just booted"

        minutes, seconds = divmod(uptime_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        else:
            return f"{minutes}m {seconds}s"

    async def fadeout_panel(self):
        """Fade out the panel before deleting it."""
        try:
            embed = self.message.embeds[0]
            embed.description = "✅ **Operation completed successfully. Closing panel...**"
            embed.color = discord.Color.green()

            await self.message.edit(embed=embed, view=None)
            await asyncio.sleep(2)
            await self.message.delete()
        except (discord.NotFound, discord.HTTPException):
            pass

    async def quick_ephemeral(self, interaction: discord.Interaction, content: str):
        """Send an ephemeral message that self-destructs after 10 seconds."""
        followup = await interaction.followup.send(content, ephemeral=True)
        await asyncio.sleep(10)
        try:
            await followup.edit(content="✅ This message expired.", view=None)
        except Exception:
            pass

    @discord.ui.button(label="Purge Messages", emoji="🧹", style=discord.ButtonStyle.danger)
    async def purge_messages(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        deleted = 0
        async for msg in interaction.channel.history(limit=50):
            if msg.author == self.cog.bot.user:
                if msg.id == self.message.id:
                    continue
                try:
                    await msg.delete()
                    deleted += 1
                    await asyncio.sleep(0.5)  # Slow down to avoid rate limits
                except Exception:
                    pass
                if deleted >= 10:
                    break

        await self.quick_ephemeral(interaction, f"🧹 Purged {deleted} messages.")
        await self.fadeout_panel()

    # @discord.ui.button(label="Sync Commands", emoji="🔄", style=discord.ButtonStyle.primary)
    # async def sync_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     await interaction.response.defer(ephemeral=True)

    #     await self.cog.tree.sync()
    #     await self.quick_ephemeral(interaction, "🔄 Global slash commands synced! (May take up to 1 hour)")
    #     await self.fadeout_panel()

    # @discord.ui.button(label="Reload Music Cog", emoji="📂", style=discord.ButtonStyle.success)
    # async def reload_music(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     await interaction.response.defer(ephemeral=True)

    #     try:
    #         await self.cog.bot.reload_extension("cogs.music")
    #         result = "✅ Reloaded `cogs.music` successfully!"
    #     except Exception as e:
    #         result = f"❌ Failed to reload music cog: {e}"

    #     await self.quick_ephemeral(interaction, result)
    #     await self.fadeout_panel()

    @discord.ui.button(label="Reload Maintenance Cog", emoji="🛠️", style=discord.ButtonStyle.success)
    async def reload_maintenance(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        try:
            await self.cog.bot.reload_extension("cogs.maintenance")
            result = "✅ Reloaded `cogs.maintenance` successfully!"
        except Exception as e:
            result = f"❌ Failed to reload maintenance cog: {e}"

        await self.quick_ephemeral(interaction, result)
        await self.fadeout_panel()

    @discord.ui.button(label="Restart Bot", emoji="♻️", style=discord.ButtonStyle.success)
    async def restart_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.quick_ephemeral(interaction, "♻️ Restarting bot...")
        await self.fadeout_panel()
        await asyncio.sleep(1)
        os._exit(0)

    @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.delete()
        except (discord.NotFound, discord.HTTPException):
            pass

class Maintenance(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tree = bot.tree
        self.start_time = time.time()  # Track when bot started

    @app_commands.guild_only()
    @app_commands.command(name="maintenance", description="Opens the maintenance control panel (owner only)")
    async def maintenance_panel(self, inter: discord.Interaction):
        if inter.user.id != OWNER_ID:
            return await inter.response.send_message("❌ You are not authorized to run this command.", ephemeral=True)

        embed = discord.Embed(
            title="🛠️ Fvi-Furr Maintenance Panel",
            description=f"Use the buttons below to perform maintenance actions.\n\n**Uptime:** {self.get_uptime_string()}",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Panel will timeout after 60 seconds.")

        await inter.response.send_message(embed=embed)  # <- NO "view=None" here
        sent_message = await inter.original_response()

        view = MaintenanceView(self, message=sent_message)
        await sent_message.edit(view=view)  # Attach the actual button view


    def get_uptime_string(self) -> str:
        uptime_seconds = int(time.time() - self.start_time)
        
        if uptime_seconds < 60:
            return "Just booted"
        
        minutes, seconds = divmod(uptime_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        else:
            return f"{minutes}m {seconds}s"

async def setup(bot: commands.Bot):
    await bot.add_cog(Maintenance(bot))
