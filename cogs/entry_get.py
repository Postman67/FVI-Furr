# Cog to handle entry retrieval

import asyncio
import os
import time
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import pymysql as mariadb

class EntryGet(commands.Cog):
    """Cog for retrieving stall entries from the database"""
    
    def __init__(self, bot):
        self.bot = bot
        
    def get_db_connection(self):
        """Get database connection"""
        try:
            conn = mariadb.connect(
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                host="furryville-index.db",
                database="furryville"
            )
            return conn
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB: {e}")
            return None

    def create_stall_embed(self, table_name: str, stall_data: dict) -> discord.Embed:
        """Create an embed for stall information"""
        # Define table-specific configurations for easy modification
        table_configs = {
            "warp_hall": {
                "title": "Warp Hall Stall",
                "color": 0xffd966,  # Yellow
                "fields": [
                    ("Stall Number", "StallNumber"),
                    ("Owner IGN", "IGN"),
                    ("Stall Name", "StallName")
                ]
            },
            "the_mall": {
                "title": "The Mall Stall",
                "color": 0xffd966,  # Yellow
                "fields": [
                    ("Stall Number", "StallNumber"),
                    ("Street Name", "StreetName"),
                    ("Owner IGN", "IGN"),
                    ("Stall Name", "StallName"),
                    ("Items Sold", "ItemsSold")
                ]
            }
        }
        
        config = table_configs.get(table_name)
        if not config:
            return None
            
        embed = discord.Embed(
            title=f"{config['title']} #{stall_data.get('StallNumber', 'Unknown')}",
            color=config["color"]
        )
        
        # Add fields dynamically based on configuration
        for field_name, db_column in config["fields"]:
            value = stall_data.get(db_column, "Not Available")
            embed.add_field(name=field_name, value=value, inline=True)
            
        embed.set_footer(text="Furryville Index Database")
        return embed

    async def get_stall_data(self, table_name: str, stall_number: int) -> dict:
        """Get stall data from the specified table"""
        conn = self.get_db_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            
            # Define table-specific queries for easy modification
            table_queries = {
                "warp_hall": "SELECT StallNumber, IGN, StallName FROM warp_hall WHERE StallNumber = %s",
                "the_mall": "SELECT StallNumber, StreetName, IGN, StallName, ItemsSold FROM the_mall WHERE StallNumber = %s"
            }
            
            query = table_queries.get(table_name)
            if not query:
                return {"error": f"Unknown table: {table_name}"}
            
            cursor.execute(query, (stall_number,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if not result:
                return {"error": f"No stall found with number {stall_number} in {table_name}"}
            
            # Define column mappings for easy modification
            column_mappings = {
                "warp_hall": ["StallNumber", "IGN", "StallName"],
                "the_mall": ["StallNumber", "StreetName", "IGN", "StallName", "ItemsSold"]
            }
            
            columns = column_mappings.get(table_name, [])
            return dict(zip(columns, result))
            
        except mariadb.Error as e:
            print(f"Error querying {table_name}: {e}")
            if conn:
                conn.close()
            return {"error": f"Database query failed: {str(e)}"}

    @app_commands.command(name="stallview", description="View details of a specific stall")
    @app_commands.describe(
        table="The location to search (warp or mall)",
        stall_number="The stall number to look up"
    )
    @app_commands.choices(table=[
        app_commands.Choice(name="Warp Hall", value="warp_hall"),
        app_commands.Choice(name="The Mall", value="the_mall")
    ])
    async def stallview(self, interaction: discord.Interaction, table: app_commands.Choice[str], stall_number: int):
        """View details of a specific stall"""
        await interaction.response.defer()
        
        # Validate stall number
        if stall_number <= 0:
            embed = discord.Embed(
                title="Invalid Stall Number",
                description="Stall number must be a positive integer.",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Get stall data
        stall_data = await self.get_stall_data(table.value, stall_number)
        
        if "error" in stall_data:
            embed = discord.Embed(
                title="Error",
                description=stall_data["error"],
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Create and send embed
        embed = self.create_stall_embed(table.value, stall_data)
        if embed:
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to create embed for stall data.",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed)

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(EntryGet(bot))