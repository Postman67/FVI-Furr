# Cog to handle entry retrieval

import asyncio
import os
import time
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import pymysql as mariadb

def has_bot_permissions():
    """Check if user has the required role or is the bot owner"""
    async def predicate(interaction: discord.Interaction) -> bool:
        # Get environment variables
        postman_id = int(os.getenv('POSTMAN_ID'))
        bot_role_id = int(os.getenv('BOTROLE_ID'))
        
        # Allow POSTMAN_ID user always
        if interaction.user.id == postman_id:
            return True
        
        # Check if user has the required role
        if hasattr(interaction.user, 'roles'):
            for role in interaction.user.roles:
                if role.id == bot_role_id:
                    return True
        
        # If no permissions, send error message
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You don't have permission to use this bot's commands.",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    
    return app_commands.check(predicate)

class StreetSelectionView(discord.ui.View):
    """View for selecting street name when viewing The Mall stalls"""
    
    VALID_STREETS = [
        "Wall Street",
        "Artist Alley", 
        "Woke Ave",
        "Five",
        "Poland Street"
    ]
    
    def __init__(self, stall_number, cog, timeout=300):
        super().__init__(timeout=timeout)
        self.stall_number = stall_number
        self.cog = cog
        
        # Create dropdown with street options
        select = discord.ui.Select(
            placeholder="Select the street name for this stall...",
            options=[
                discord.SelectOption(label=street, value=street, description=f"View stall #{stall_number} on {street}")
                for street in self.VALID_STREETS
            ]
        )
        select.callback = self.street_selected
        self.add_item(select)
    
    async def street_selected(self, interaction: discord.Interaction):
        """Handle street selection and show stall data"""
        street_name = interaction.data['values'][0]
        
        # Get stall data with specific street
        stall_data = await self.cog.get_stall_data_with_street("the_mall", self.stall_number, street_name)
        
        if "error" in stall_data:
            embed = discord.Embed(
                title="Error",
                description=stall_data["error"],
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create and send embed
        embed = self.cog.create_stall_embed("the_mall", stall_data)
        if embed:
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to create embed for stall data.",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

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
        # Format stall number to display as integer if it's a whole number
        stall_number = stall_data.get('StallNumber', 'Unknown')
        if isinstance(stall_number, float) and stall_number.is_integer():
            stall_number_display = str(int(stall_number))
        else:
            stall_number_display = str(stall_number)
        
        # Define table-specific configurations for easy modification
        table_configs = {
            "warp_hall": {
                "title": "Warp Hall Stall",
                "color": 0xffd966,  # Yellow
                "fields": [
                    ("Stall Number", stall_number_display),
                    ("Owner IGN", "IGN"),
                    ("Stall Name", "StallName")
                ]
            },
            "the_mall": {
                "title": "The Mall Stall",
                "color": 0xffd966,  # Yellow
                "fields": [
                    ("Stall Number", stall_number_display),
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
            title=f"{config['title']} #{stall_number_display}",
            color=config["color"]
        )
        
        # Add fields dynamically based on configuration
        for field_name, db_column in config["fields"]:
            if field_name == "Stall Number":
                # Use the already formatted stall number
                value = db_column  # This is already the formatted display value
            else:
                value = stall_data.get(db_column, "Not Available")
            embed.add_field(name=field_name, value=value, inline=True)
            
        embed.set_footer(text="Furryville Index Database")
        return embed

    async def get_stall_data(self, table_name: str, stall_number) -> dict:
        """Get stall data from the specified table (Warp Hall only)"""
        if table_name != "warp_hall":
            return {"error": "This method only supports Warp Hall. Use get_stall_data_with_street for The Mall."}
            
        conn = self.get_db_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            
            query = "SELECT StallNumber, IGN, StallName FROM warp_hall WHERE StallNumber = %s"
            cursor.execute(query, (stall_number,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if not result:
                return {"error": f"No stall found with number {stall_number} in Warp Hall"}
            
            columns = ["StallNumber", "IGN", "StallName"]
            return dict(zip(columns, result))
            
        except mariadb.Error as e:
            print(f"Error querying warp_hall: {e}")
            if conn:
                conn.close()
            return {"error": f"Database query failed: {str(e)}"}

    async def get_stall_data_with_street(self, table_name: str, stall_number, street_name: str) -> dict:
        """Get stall data from The Mall with specific street name"""
        conn = self.get_db_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            
            query = "SELECT StallNumber, StreetName, IGN, StallName, ItemsSold FROM the_mall WHERE StallNumber = %s AND StreetName = %s"
            cursor.execute(query, (stall_number, street_name))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if not result:
                return {"error": f"No stall found with number {stall_number} on {street_name}"}
            
            columns = ["StallNumber", "StreetName", "IGN", "StallName", "ItemsSold"]
            return dict(zip(columns, result))
            
        except mariadb.Error as e:
            print(f"Error querying the_mall: {e}")
            if conn:
                conn.close()
            return {"error": f"Database query failed: {str(e)}"}

    async def check_mall_stall_exists(self, stall_number) -> dict:
        """Check if a stall number exists in The Mall (any street)"""
        conn = self.get_db_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            
            query = "SELECT COUNT(*) FROM the_mall WHERE StallNumber = %s"
            cursor.execute(query, (stall_number,))
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            if count == 0:
                return {"error": f"No stall found with number {stall_number} in The Mall"}
            
            return {"exists": True, "count": count}
            
        except mariadb.Error as e:
            print(f"Error checking the_mall: {e}")
            if conn:
                conn.close()
            return {"error": f"Database query failed: {str(e)}"}

    @app_commands.command(name="stallview", description="View details of a specific stall")
    @app_commands.describe(
        table="The location to search (warp or mall)",
        stall_number="The stall number to look up (integers for Warp Hall, decimals allowed for The Mall)"
    )
    @app_commands.choices(table=[
        app_commands.Choice(name="Warp Hall", value="warp_hall"),
        app_commands.Choice(name="The Mall", value="the_mall")
    ])
    @has_bot_permissions()
    async def stallview(self, interaction: discord.Interaction, table: app_commands.Choice[str], stall_number: float):
        """View details of a specific stall"""
        
        # Validate stall number based on table type
        if table.value == "warp_hall":
            # Warp Hall requires integers
            if not isinstance(stall_number, int) and not stall_number.is_integer():
                embed = discord.Embed(
                    title="Invalid Stall Number",
                    description="Warp Hall stall numbers must be whole numbers (integers).",
                    color=0xe74c3c
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            stall_number = int(stall_number)
        
        if stall_number <= 0:
            embed = discord.Embed(
                title="Invalid Stall Number",
                description="Stall number must be a positive number.",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if table.value == "warp_hall":
            # For Warp Hall, directly get and show stall data
            await interaction.response.defer()
            
            stall_data = await self.get_stall_data("warp_hall", stall_number)
            
            if "error" in stall_data:
                embed = discord.Embed(
                    title="Error",
                    description=stall_data["error"],
                    color=0xe74c3c
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create and send embed
            embed = self.create_stall_embed("warp_hall", stall_data)
            if embed:
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Error",
                    description="Failed to create embed for stall data.",
                    color=0xe74c3c
                )
                await interaction.followup.send(embed=embed)
                
        else:  # the_mall
            # For The Mall, first check if stall exists, then show street selection
            await interaction.response.defer(ephemeral=True)
            
            stall_check = await self.check_mall_stall_exists(stall_number)
            
            if "error" in stall_check:
                embed = discord.Embed(
                    title="Error",
                    description=stall_check["error"],
                    color=0xe74c3c
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Show street selection dropdown
            view = StreetSelectionView(stall_number, self)
            embed = discord.Embed(
                title="Select Street Name",
                description=f"Stall #{stall_number} found in The Mall. Please select which street to view:",
                color=0x3498db
            )
            
            if stall_check.get("count", 0) > 1:
                embed.add_field(
                    name="Multiple Locations", 
                    value=f"This stall number exists on {stall_check['count']} different streets.", 
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(EntryGet(bot))