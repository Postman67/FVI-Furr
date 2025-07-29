# Cog to handle entry creation

import asyncio
import os
import time
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import pymysql as mariadb

class StreetNameTransformer(app_commands.Transformer):
    """Transformer for street name autocomplete"""
    
    VALID_STREETS = [
        "Wall Street",
        "Artist Alley", 
        "Woke Ave",
        "Five",
        "Poland Street"
    ]
    
    async def transform(self, interaction: discord.Interaction, value: str) -> str:
        return value
    
    async def autocomplete(self, interaction: discord.Interaction, value: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=street, value=street)
            for street in self.VALID_STREETS
            if value.lower() in street.lower()
        ][:25]

class StallCreationModal(discord.ui.Modal):
    """Modal for creating stall entries"""
    
    def __init__(self, table_name: str, cog):
        self.table_name = table_name
        self.cog = cog
        
        if table_name == "warp_hall":
            title = "Create Warp Hall Stall"
        else:
            title = "Create The Mall Stall"
            
        super().__init__(title=title, timeout=300)
        
        # Common fields
        self.stall_number = discord.ui.TextInput(
            label="Stall Number",
            placeholder="Enter the stall number (e.g., 1, 2, 3...)",
            required=True,
            max_length=10
        )
        self.add_item(self.stall_number)
        
        self.ign = discord.ui.TextInput(
            label="Owner IGN",
            placeholder="Enter the owner's in-game name",
            required=True,
            max_length=50
        )
        self.add_item(self.ign)
        
        self.stall_name = discord.ui.TextInput(
            label="Stall Name",
            placeholder="Enter the stall name",
            required=True,
            max_length=100
        )
        self.add_item(self.stall_name)
        
        # Mall-specific fields
        if table_name == "the_mall":
            self.street_name = discord.ui.TextInput(
                label="Street Name",
                placeholder="Wall Street, Artist Alley, Woke Ave, Five, Poland Street",
                required=True,
                max_length=50
            )
            self.add_item(self.street_name)
            
            self.items_sold = discord.ui.TextInput(
                label="Items Sold",
                placeholder="Describe what items are sold at this stall",
                required=True,
                max_length=200,
                style=discord.TextStyle.paragraph
            )
            self.add_item(self.items_sold)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Validate stall number
        try:
            stall_num = int(self.stall_number.value)
            if stall_num <= 0:
                raise ValueError("Stall number must be positive")
        except ValueError:
            embed = discord.Embed(
                title="Invalid Stall Number",
                description="Stall number must be a positive integer.",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Validate street name for The Mall
        if self.table_name == "the_mall":
            if self.street_name.value not in StreetNameTransformer.VALID_STREETS:
                embed = discord.Embed(
                    title="Invalid Street Name",
                    description=f"Street name must be one of: {', '.join(StreetNameTransformer.VALID_STREETS)}",
                    color=0xe74c3c
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        # Prepare data
        if self.table_name == "warp_hall":
            data = {
                "StallNumber": stall_num,
                "IGN": self.ign.value,
                "StallName": self.stall_name.value
            }
        else:  # the_mall
            data = {
                "StallNumber": stall_num,
                "StreetName": self.street_name.value,
                "IGN": self.ign.value,
                "StallName": self.stall_name.value,
                "ItemsSold": self.items_sold.value
            }
        
        # Create the entry
        result = await self.cog.create_stall_entry(self.table_name, data)
        
        if result["success"]:
            embed = self.cog.create_success_embed(self.table_name, data)
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error Creating Stall",
                description=result["error"],
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class EntryCreate(commands.Cog):
    """Cog for creating stall entries in the database"""
    
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

    async def create_stall_entry(self, table_name: str, data: dict) -> dict:
        """Create a new stall entry in the database"""
        conn = self.get_db_connection()
        if not conn:
            return {"success": False, "error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            
            # Check if entry already exists based on table type
            if table_name == "warp_hall":
                # For Warp Hall, only check StallNumber (single primary key)
                check_query = "SELECT StallNumber FROM warp_hall WHERE StallNumber = %s"
                cursor.execute(check_query, (data["StallNumber"],))
                if cursor.fetchone():
                    cursor.close()
                    conn.close()
                    return {"success": False, "error": f"Stall number {data['StallNumber']} already exists in Warp Hall"}
                
                # Insert the new entry
                insert_query = "INSERT INTO warp_hall (StallNumber, IGN, StallName) VALUES (%s, %s, %s)"
                values = (data["StallNumber"], data["IGN"], data["StallName"])
                
            else:  # the_mall
                # For The Mall, check both StallNumber AND StreetName (composite primary key)
                check_query = "SELECT StallNumber FROM the_mall WHERE StallNumber = %s AND StreetName = %s"
                cursor.execute(check_query, (data["StallNumber"], data["StreetName"]))
                if cursor.fetchone():
                    cursor.close()
                    conn.close()
                    return {"success": False, "error": f"Stall number {data['StallNumber']} already exists on {data['StreetName']}"}
                
                # Insert the new entry
                insert_query = "INSERT INTO the_mall (StallNumber, StreetName, IGN, StallName, ItemsSold) VALUES (%s, %s, %s, %s, %s)"
                values = (data["StallNumber"], data["StreetName"], data["IGN"], data["StallName"], data["ItemsSold"])
            
            cursor.execute(insert_query, values)
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return {"success": True}
            
        except mariadb.Error as e:
            print(f"Error creating entry in {table_name}: {e}")
            if conn:
                conn.close()
            return {"success": False, "error": f"Database error: {str(e)}"}

    def create_success_embed(self, table_name: str, data: dict) -> discord.Embed:
        """Create a success embed for the created stall"""
        if table_name == "warp_hall":
            embed = discord.Embed(
                title="✅ Warp Hall Stall Created Successfully!",
                color=0x00ff00
            )
            embed.add_field(name="Stall Number", value=data["StallNumber"], inline=True)
            embed.add_field(name="Owner IGN", value=data["IGN"], inline=True)
            embed.add_field(name="Stall Name", value=data["StallName"], inline=True)
        else:  # the_mall
            embed = discord.Embed(
                title="✅ The Mall Stall Created Successfully!",
                color=0x00ff00
            )
            embed.add_field(name="Stall Number", value=data["StallNumber"], inline=True)
            embed.add_field(name="Street Name", value=data["StreetName"], inline=True)
            embed.add_field(name="Owner IGN", value=data["IGN"], inline=True)
            embed.add_field(name="Stall Name", value=data["StallName"], inline=False)
            embed.add_field(name="Items Sold", value=data["ItemsSold"], inline=False)
        
        embed.set_footer(text="Furryville Index Database")
        return embed

    @app_commands.command(name="stallcreate", description="Create a new stall entry using an interactive form")
    @app_commands.describe(table="Choose which location to create a stall in")
    @app_commands.choices(table=[
        app_commands.Choice(name="Warp Hall", value="warp_hall"),
        app_commands.Choice(name="The Mall", value="the_mall")
    ])
    async def stallcreate(self, interaction: discord.Interaction, table: app_commands.Choice[str]):
        """Create a new stall entry using an interactive modal form"""
        modal = StallCreationModal(table.value, self)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="stallcreatetm", description="Create a new The Mall stall entry")
    @app_commands.describe(
        stall_number="The stall number",
        street_name="The street name",
        ign="Owner's in-game name", 
        stall_name="Name of the stall",
        items_sold="Items sold at this stall"
    )
    async def stallcreatetm(
        self, 
        interaction: discord.Interaction, 
        stall_number: int,
        street_name: app_commands.Transform[str, StreetNameTransformer],
        ign: str,
        stall_name: str,
        items_sold: str
    ):
        """Create a new The Mall stall entry with inline parameters"""
        await interaction.response.defer()
        
        # Validate stall number
        if stall_number <= 0:
            embed = discord.Embed(
                title="Invalid Stall Number",
                description="Stall number must be a positive integer.",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Validate street name
        if street_name not in StreetNameTransformer.VALID_STREETS:
            embed = discord.Embed(
                title="Invalid Street Name",
                description=f"Street name must be one of: {', '.join(StreetNameTransformer.VALID_STREETS)}",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Prepare data
        data = {
            "StallNumber": stall_number,
            "StreetName": street_name,
            "IGN": ign,
            "StallName": stall_name,
            "ItemsSold": items_sold
        }
        
        # Create the entry
        result = await self.create_stall_entry("the_mall", data)
        
        if result["success"]:
            embed = self.create_success_embed("the_mall", data)
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error Creating Stall",
                description=result["error"],
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="stallcreatewh", description="Create a new Warp Hall stall entry")
    @app_commands.describe(
        stall_number="The stall number",
        ign="Owner's in-game name",
        stall_name="Name of the stall"
    )
    async def stallcreatewh(
        self,
        interaction: discord.Interaction,
        stall_number: int,
        ign: str,
        stall_name: str
    ):
        """Create a new Warp Hall stall entry with inline parameters"""
        await interaction.response.defer()
        
        # Validate stall number
        if stall_number <= 0:
            embed = discord.Embed(
                title="Invalid Stall Number", 
                description="Stall number must be a positive integer.",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Prepare data
        data = {
            "StallNumber": stall_number,
            "IGN": ign,
            "StallName": stall_name
        }
        
        # Create the entry
        result = await self.create_stall_entry("warp_hall", data)
        
        if result["success"]:
            embed = self.create_success_embed("warp_hall", data)
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error Creating Stall",
                description=result["error"],
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(EntryCreate(bot))