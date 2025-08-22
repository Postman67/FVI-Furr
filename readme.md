# FVI-Furr
### Discord bot to server the greater needs of the Furryville index

Bot will not work unless you have a .env file with the required fields

## Cogs Info
#### - Maintenence Cog
Serves as the in-Discord control center. Show uptime, purge messages, and restart the bot.

#### - Entry Create
Create an entry on either Warp Hall or The Mall

#### - Entry Edit
Edit an existing entry on either table

#### - Entry Get
Lists all information (all collumns) of an table entry

## DB Formatting
#### Table Name: warp_hall

- Stall Number (StallNumber) (warp_hall_pk)
- Owner IGN (IGN)
- Stall Name (StallName)

#### Table Name: the_mall

- Stall Number (StallNumber) (the_mall_pk)
- Street Name (StreetName)
- Owner IGN (IGN)
- Stall Name (StallName)
- Items Sold (ItemsSold)

## The Mall Street Names
- Wall Street
- Artist Alley
- Woke Ave
- Five
- Poland Street

## The Mall Review entry format
Table Name: the_mall_reviews
- ReviewID (INT)
- StallNumber (INT)
- StreetName (String)
- ReviewerID (BIGINT)
- ReviewerName (String)
- ReviewText (String) (Review Text)
- Rating (INT)
- CreatedAt (DATETIME)
- UpdatedAt (DATETIME)