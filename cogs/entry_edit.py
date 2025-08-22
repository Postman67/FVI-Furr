# Cog to handle entry edits

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
    """View for selecting street name when editing The Mall stalls"""
    
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
                discord.SelectOption(label=street, value=street, description=f"Edit stall on {street}")
                for street in self.VALID_STREETS
            ]
        )
        select.callback = self.street_selected
        self.add_item(select)
    
    async def street_selected(self, interaction: discord.Interaction):
        """Handle street selection and open edit modal"""
        street_name = interaction.data['values'][0]
        
        # Get existing stall data
        stall_data = await self.cog.get_stall_data("the_mall", self.stall_number, street_name)
        
        if "error" in stall_data:
            embed = discord.Embed(
                title="Error",
                description=stall_data["error"],
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Open edit modal with pre-filled data
        modal = StallEditModal("the_mall", stall_data, self.cog)
        await interaction.response.send_modal(modal)

class StallEditModal(discord.ui.Modal):
    """Modal for editing stall entries with pre-filled data"""
    
    def __init__(self, table_name: str, existing_data: dict, cog):
        self.table_name = table_name
        self.existing_data = existing_data
        self.cog = cog
        
        if table_name == "warp_hall":
            title = f"Edit Warp Hall Stall #{existing_data.get('StallNumber', '?')}"
        else:
            title = f"Edit The Mall Stall #{existing_data.get('StallNumber', '?')}"
            
        super().__init__(title=title, timeout=300)
        
        # Pre-fill common fields
        self.ign = discord.ui.TextInput(
            label="Owner IGN",
            placeholder="Leave empty to keep current value",
            default=existing_data.get("IGN", ""),
            required=False,
            max_length=50
        )
        self.add_item(self.ign)
        
        self.stall_name = discord.ui.TextInput(
            label="Stall Name",
            placeholder="Leave empty to keep current value",
            default=existing_data.get("StallName", ""),
            required=False,
            max_length=100
        )
        self.add_item(self.stall_name)
        
        # Mall-specific fields
        if table_name == "the_mall":
            self.items_sold = discord.ui.TextInput(
                label="Items Sold",
                placeholder="Leave empty to keep current value",
                default=existing_data.get("ItemsSold", ""),
                required=False,
                max_length=200,
                style=discord.TextStyle.paragraph
            )
            self.add_item(self.items_sold)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Prepare update data - only include non-empty fields
        update_data = {}
        
        if self.ign.value.strip():
            update_data["IGN"] = self.ign.value.strip()
        
        if self.stall_name.value.strip():
            update_data["StallName"] = self.stall_name.value.strip()
        
        if self.table_name == "the_mall":
            if self.items_sold.value.strip():
                update_data["ItemsSold"] = self.items_sold.value.strip()
        
        # Check if any changes were made
        if not update_data:
            embed = discord.Embed(
                title="No Changes Made",
                description="All fields were empty, so no changes were applied to the stall.",
                color=0xffaa00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Update the entry
        result = await self.cog.update_stall_entry(self.table_name, self.existing_data["StallNumber"], update_data, self.existing_data.get("StreetName"))
        
        if result["success"]:
            # Get updated data for embed
            updated_data = self.existing_data.copy()
            updated_data.update(update_data)
            
            embed = self.cog.create_edit_success_embed(self.table_name, updated_data, update_data)
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error Updating Stall",
                description=result["error"],
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class EntryEdit(commands.Cog):
    """Cog for editing stall entries in the database"""
    
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

    async def get_stall_data(self, table_name: str, stall_number, street_name: str = None) -> dict:
        """Get stall data from the specified table"""
        conn = self.get_db_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            
            if table_name == "warp_hall":
                query = "SELECT StallNumber, IGN, StallName FROM warp_hall WHERE StallNumber = %s"
                cursor.execute(query, (stall_number,))
                result = cursor.fetchone()
                
                if not result:
                    cursor.close()
                    conn.close()
                    return {"error": f"No stall found with number {stall_number} in Warp Hall"}
                
                cursor.close()
                conn.close()
                return {
                    "StallNumber": result[0],
                    "IGN": result[1],
                    "StallName": result[2]
                }
            
            else:  # the_mall
                if street_name:
                    # Get specific stall by number and street
                    query = "SELECT StallNumber, StreetName, IGN, StallName, ItemsSold FROM the_mall WHERE StallNumber = %s AND StreetName = %s"
                    cursor.execute(query, (stall_number, street_name))
                    result = cursor.fetchone()
                    
                    if not result:
                        cursor.close()
                        conn.close()
                        return {"error": f"No stall found with number {stall_number} on {street_name}"}
                    
                    cursor.close()
                    conn.close()
                    return {
                        "StallNumber": result[0],
                        "StreetName": result[1],
                        "IGN": result[2],
                        "StallName": result[3],
                        "ItemsSold": result[4]
                    }
                else:
                    # Check if stall number exists (for street selection)
                    query = "SELECT COUNT(*) FROM the_mall WHERE StallNumber = %s"
                    cursor.execute(query, (stall_number,))
                    count = cursor.fetchone()[0]
                    
                    cursor.close()
                    conn.close()
                    
                    if count == 0:
                        return {"error": f"No stall found with number {stall_number} in The Mall"}
                    
                    return {"exists": True}
            
        except mariadb.Error as e:
            print(f"Error querying {table_name}: {e}")
            if conn:
                conn.close()
            return {"error": f"Database query failed: {str(e)}"}

    async def update_stall_entry(self, table_name: str, stall_number, update_data: dict, street_name: str = None) -> dict:
        """Update a stall entry in the database"""
        conn = self.get_db_connection()
        if not conn:
            return {"success": False, "error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            
            # Build UPDATE query dynamically
            set_clauses = []
            values = []
            
            for field, value in update_data.items():
                set_clauses.append(f"{field} = %s")
                values.append(value)
            
            if table_name == "warp_hall":
                query = f"UPDATE warp_hall SET {', '.join(set_clauses)} WHERE StallNumber = %s"
                values.append(stall_number)
            else:  # the_mall
                query = f"UPDATE the_mall SET {', '.join(set_clauses)} WHERE StallNumber = %s AND StreetName = %s"
                values.extend([stall_number, street_name])
            
            cursor.execute(query, values)
            
            if cursor.rowcount == 0:
                cursor.close()
                conn.close()
                return {"success": False, "error": "No rows were updated. Stall may not exist."}
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {"success": True}
            
        except mariadb.Error as e:
            print(f"Error updating entry in {table_name}: {e}")
            if conn:
                conn.close()
            return {"success": False, "error": f"Database error: {str(e)}"}

    def create_edit_success_embed(self, table_name: str, stall_data: dict, updated_fields: dict) -> discord.Embed:
        """Create a success embed for the edited stall"""
        # Format stall number to display as integer if it's a whole number
        stall_number = stall_data["StallNumber"]
        if isinstance(stall_number, float) and stall_number.is_integer():
            stall_number_display = str(int(stall_number))
        else:
            stall_number_display = str(stall_number)
        
        if table_name == "warp_hall":
            embed = discord.Embed(
                title="✅ Warp Hall Stall Updated Successfully!",
                color=0x00ff00
            )
            embed.add_field(name="Stall Number", value=stall_number_display, inline=True)
            embed.add_field(name="Owner IGN", value=stall_data["IGN"], inline=True)
            embed.add_field(name="Stall Name", value=stall_data["StallName"], inline=True)
        else:  # the_mall
            embed = discord.Embed(
                title="✅ The Mall Stall Updated Successfully!",
                color=0x00ff00
            )
            embed.add_field(name="Stall Number", value=stall_number_display, inline=True)
            embed.add_field(name="Street Name", value=stall_data["StreetName"], inline=True)
            embed.add_field(name="Owner IGN", value=stall_data["IGN"], inline=True)
            embed.add_field(name="Stall Name", value=stall_data["StallName"], inline=False)
            embed.add_field(name="Items Sold", value=stall_data["ItemsSold"], inline=False)
        
        # Add information about what was updated
        updated_field_names = []
        for field in updated_fields.keys():
            if field == "IGN":
                updated_field_names.append("Owner IGN")
            elif field == "StallName":
                updated_field_names.append("Stall Name")
            elif field == "ItemsSold":
                updated_field_names.append("Items Sold")
            else:
                updated_field_names.append(field)
        
        embed.add_field(
            name="Updated Fields", 
            value=", ".join(updated_field_names), 
            inline=False
        )
        
        embed.set_footer(text="Furryville Index Database")
        return embed

    @app_commands.command(name="stalledit", description="Edit an existing stall entry")
    @app_commands.describe(
        table="Choose which location to edit a stall in",
        stall_number="The stall number to edit (integers for Warp Hall, decimals allowed for The Mall)"
    )
    @app_commands.choices(table=[
        app_commands.Choice(name="Warp Hall", value="warp_hall"),
        app_commands.Choice(name="The Mall", value="the_mall")
    ])
    @has_bot_permissions()
    async def stalledit(self, interaction: discord.Interaction, table: app_commands.Choice[str], stall_number: float):
        """Edit an existing stall entry"""
        
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
            # For Warp Hall, directly get data and show edit modal
            # We need to defer here because we're doing database operations
            await interaction.response.defer(ephemeral=True)
            
            stall_data = await self.get_stall_data("warp_hall", stall_number)
            
            if "error" in stall_data:
                embed = discord.Embed(
                    title="Error",
                    description=stall_data["error"],
                    color=0xe74c3c
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create a button that will open the modal
            class EditButton(discord.ui.View):
                def __init__(self, stall_data, cog):
                    super().__init__(timeout=60)
                    self.stall_data = stall_data
                    self.cog = cog
                
                @discord.ui.button(label="Open Edit Form", style=discord.ButtonStyle.primary, emoji="✏️")
                async def open_edit_modal(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    modal = StallEditModal("warp_hall", self.stall_data, self.cog)
                    await button_interaction.response.send_modal(modal)
            
            embed = discord.Embed(
                title="Warp Hall Stall Found",
                description=f"Stall #{stall_number} found. Click the button below to open the edit form.",
                color=0x3498db
            )
            embed.add_field(name="Current Owner IGN", value=stall_data["IGN"], inline=True)
            embed.add_field(name="Current Stall Name", value=stall_data["StallName"], inline=True)
            
            view = EditButton(stall_data, self)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        else:  # the_mall
            # For The Mall, first check if stall exists, then show street selection
            await interaction.response.defer(ephemeral=True)
            
            stall_check = await self.get_stall_data("the_mall", stall_number)
            
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
                description=f"Please select which street the stall #{stall_number} is located on:",
                color=0x3498db
            )
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(EntryEdit(bot))
