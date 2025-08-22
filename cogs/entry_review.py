# Cog to handle The Mall stall reviews

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

class ReviewModal(discord.ui.Modal):
    """Modal for submitting The Mall stall reviews"""
    
    def __init__(self, stall_number, street_name: str, cog=None, existing_review=None):
        self.stall_number = stall_number
        self.street_name = street_name
        self.cog = cog
        self.is_update = existing_review is not None
        
        if self.is_update:
            title = f"Edit Review for The Mall Stall #{stall_number} on {street_name}"
        else:
            title = f"Review The Mall Stall #{stall_number} on {street_name}"
            
        super().__init__(title=title, timeout=300)
        
        # Rating field (1-5) - prefill if editing
        rating_default = str(existing_review["rating"]) if existing_review else ""
        self.rating = discord.ui.TextInput(
            label="Rating (1-5 stars)",
            placeholder="Enter a rating from 1 to 5",
            default=rating_default,
            required=True,
            max_length=1
        )
        self.add_item(self.rating)
        
        # Review text - prefill if editing
        review_default = existing_review["review_text"] if existing_review else ""
        self.review_text = discord.ui.TextInput(
            label="Review",
            placeholder="Write your review of this stall...",
            default=review_default,
            required=True,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.review_text)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Validate rating
        try:
            rating = int(self.rating.value)
            if rating < 1 or rating > 5:
                raise ValueError("Rating must be between 1 and 5")
        except ValueError:
            embed = discord.Embed(
                title="Invalid Rating",
                description="Rating must be a number between 1 and 5.",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Prepare review data
        review_data = {
            "ReviewerID": interaction.user.id,
            "ReviewerName": interaction.user.display_name,
            "StallNumber": self.stall_number,
            "StreetName": self.street_name,
            "Rating": rating,
            "ReviewText": self.review_text.value
        }
        
        # Submit review
        result = await self.cog.create_or_update_review(review_data, self.is_update)
        
        if result["success"]:
            embed = self.cog.create_review_success_embed(review_data, self.is_update)
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error Creating Review",
                description=result["error"],
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class EntryReview(commands.Cog):
    """Cog for handling The Mall stall reviews"""
    
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

    async def check_stall_exists(self, stall_number, street_name: str) -> bool:
        """Check if a stall exists in The Mall"""
        conn = self.get_db_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) FROM the_mall WHERE StallNumber = %s AND StreetName = %s"
            cursor.execute(query, (stall_number, street_name))
            
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            return count > 0
            
        except mariadb.Error as e:
            print(f"Error checking stall existence: {e}")
            if conn:
                conn.close()
            return False

    async def get_existing_review(self, reviewer_id: int, stall_number, street_name: str) -> dict:
        """Get existing review data for this stall, if any"""
        conn = self.get_db_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            query = "SELECT ReviewText, Rating FROM the_mall_reviews WHERE ReviewerID = %s AND StallNumber = %s AND StreetName = %s"
            cursor.execute(query, (reviewer_id, stall_number, street_name))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                return {
                    "review_text": result[0],
                    "rating": result[1],
                    "exists": True
                }
            else:
                return {"exists": False}
            
        except mariadb.Error as e:
            print(f"Error checking existing review: {e}")
            if conn:
                conn.close()
            return None

    async def update_reviewer_name(self, reviewer_id: int, new_name: str):
        """Silently update all reviews with matching ReviewerID to use the current display name"""
        conn = self.get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Check if name update is needed
            check_query = "SELECT DISTINCT ReviewerName FROM the_mall_reviews WHERE ReviewerID = %s"
            cursor.execute(check_query, (reviewer_id,))
            existing_names = cursor.fetchall()
            
            # If any existing names don't match the current name, update all entries
            needs_update = False
            for (existing_name,) in existing_names:
                if existing_name != new_name:
                    needs_update = True
                    break
            
            if needs_update:
                update_query = "UPDATE the_mall_reviews SET ReviewerName = %s WHERE ReviewerID = %s"
                cursor.execute(update_query, (new_name, reviewer_id))
                conn.commit()
            
            cursor.close()
            conn.close()
            
        except mariadb.Error as e:
            print(f"Error updating reviewer name: {e}")
            if conn:
                conn.close()

    async def create_or_update_review(self, review_data: dict, is_update: bool = False) -> dict:
        """Create a new review or update an existing one in the database"""
        conn = self.get_db_connection()
        if not conn:
            return {"success": False, "error": "Database connection failed"}
        
        try:
            cursor = conn.cursor()
            
            if is_update:
                # Update existing review
                update_query = """
                UPDATE the_mall_reviews 
                SET ReviewText = %s, Rating = %s, UpdatedAt = CURRENT_TIMESTAMP
                WHERE ReviewerID = %s AND StallNumber = %s AND StreetName = %s
                """
                values = (
                    review_data["ReviewText"],
                    review_data["Rating"],
                    review_data["ReviewerID"],
                    review_data["StallNumber"],
                    review_data["StreetName"]
                )
            else:
                # Insert new review
                insert_query = """
                INSERT INTO the_mall_reviews (StallNumber, StreetName, ReviewerID, ReviewerName, ReviewText, Rating) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                values = (
                    review_data["StallNumber"],
                    review_data["StreetName"],
                    review_data["ReviewerID"],
                    review_data["ReviewerName"],
                    review_data["ReviewText"],
                    review_data["Rating"]
                )
            
            cursor.execute(update_query if is_update else insert_query, values)
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return {"success": True}
            
        except mariadb.Error as e:
            print(f"Error creating/updating review: {e}")
            if conn:
                conn.close()
            return {"success": False, "error": f"Database error: {str(e)}"}

    def create_review_success_embed(self, review_data: dict, is_update: bool = False) -> discord.Embed:
        """Create a success embed for submitted review"""
        # Format stall number
        stall_number = review_data["StallNumber"]
        if isinstance(stall_number, float) and stall_number.is_integer():
            stall_number_display = str(int(stall_number))
        else:
            stall_number_display = str(stall_number)
        
        # Create star display
        stars = "⭐" * review_data["Rating"] + "☆" * (5 - review_data["Rating"])
        
        if is_update:
            title = f"✅ Review Updated for The Mall Stall #{stall_number_display}"
        else:
            title = f"✅ Review Submitted for The Mall Stall #{stall_number_display}"
        
        embed = discord.Embed(
            title=title,
            color=0x00ff00
        )
        
        embed.add_field(name="Reviewer", value=review_data["ReviewerName"], inline=True)
        embed.add_field(name="Stall Number", value=stall_number_display, inline=True)
        embed.add_field(name="Street", value=review_data["StreetName"], inline=True)
        embed.add_field(name="Rating", value=f"{stars} ({review_data['Rating']}/5)", inline=False)
        embed.add_field(name="Review", value=review_data["ReviewText"], inline=False)
        
        embed.set_footer(text="Furryville Index Database")
        return embed

    @app_commands.command(name="review", description="Submit a review for a The Mall stall")
    @app_commands.describe(
        stall_number="The stall number to review",
        street_name="The street name where the stall is located"
    )
    async def review(self, interaction: discord.Interaction, stall_number: float, street_name: StreetNameTransformer):
        """Submit a review for a The Mall stall"""
        
        # Validate stall number (The Mall allows decimals)
        if stall_number <= 0:
            embed = discord.Embed(
                title="Invalid Stall Number",
                description="Stall number must be a positive number.",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Validate street name
        valid_streets = [
            "Wall Street",
            "Artist Alley", 
            "Woke Ave",
            "Five",
            "Poland Street"
        ]
        
        if street_name not in valid_streets:
            embed = discord.Embed(
                title="Invalid Street Name",
                description=f"Street name must be one of: {', '.join(valid_streets)}",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Silently update reviewer name for all their reviews
        await self.update_reviewer_name(interaction.user.id, interaction.user.display_name)
        
        # Check if stall exists
        stall_exists = await self.check_stall_exists(stall_number, street_name)
        if not stall_exists:
            embed = discord.Embed(
                title="Error",
                description=f"No stall found with number {stall_number} on {street_name}",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Check for existing review
        existing_review = await self.get_existing_review(interaction.user.id, stall_number, street_name)
        if existing_review is None:
            embed = discord.Embed(
                title="Database Error",
                description="Unable to check for existing reviews. Please try again.",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Format stall number for display
        if isinstance(stall_number, float) and stall_number.is_integer():
            stall_number_display = str(int(stall_number))
        else:
            stall_number_display = str(stall_number)
        
        # Create review button with appropriate messaging
        class ReviewButton(discord.ui.View):
            def __init__(self, stall_number, street_name, cog, existing_review=None):
                super().__init__(timeout=60)
                self.stall_number = stall_number
                self.street_name = street_name
                self.cog = cog
                self.existing_review = existing_review
                self.has_existing = existing_review is not None and existing_review.get("exists", False)
            
            @discord.ui.button(label="Edit Review", style=discord.ButtonStyle.primary, emoji="📝")
            async def open_review_modal(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                # Update button label based on whether review exists
                if not self.has_existing:
                    button.label = "Write Review"
                
                modal_existing_data = self.existing_review if self.has_existing else None
                modal = ReviewModal(self.stall_number, self.street_name, self.cog, modal_existing_data)
                await button_interaction.response.send_modal(modal)
        
        if existing_review.get("exists"):
            # Show existing review info and edit option
            stars = "⭐" * existing_review["rating"] + "☆" * (5 - existing_review["rating"])
            embed = discord.Embed(
                title="Edit Your Existing Review",
                description=f"You already have a review for stall #{stall_number_display} on {street_name}. Click below to edit it.",
                color=0xffaa00
            )
            embed.add_field(name="Current Rating", value=f"{stars} ({existing_review['rating']}/5)", inline=False)
            embed.add_field(name="Current Review", value=existing_review["review_text"][:500] + ("..." if len(existing_review["review_text"]) > 500 else ""), inline=False)
            view = ReviewButton(stall_number, street_name, self, existing_review)
        else:
            # Show new review option
            embed = discord.Embed(
                title="Review The Mall Stall",
                description=f"Click the button below to submit a review for stall #{stall_number_display} on {street_name}.",
                color=0x3498db
            )
            view = ReviewButton(stall_number, street_name, self, None)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(EntryReview(bot))
