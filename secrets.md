# Secrets Configuration

This document explains all the environment variables used in the FVI-Furr Discord bot. These variables should be set in your `.env` file and kept secure.

## Discord Configuration

### DISCORD_TOKEN
- **Type**: String
- **Required**: Yes
- **Description**: The bot token from Discord Developer Portal. This is used to authenticate the bot with Discord's API.
- **Example**: `DISCORD_TOKEN=your_bot_token_here`
- **Security**: CRITICAL - Never share this token publicly. It gives full control over your bot.

### FURRYVILLE_ID
- **Type**: Integer (Discord Snowflake)
- **Required**: Yes
- **Description**: The Discord server ID for the Furryville server. Used to sync slash commands to this specific guild.
- **Example**: `FURRYVILLE_ID=123456789012345678`
- **How to get**: Right-click on the server name in Discord → Copy Server ID (requires Developer Mode enabled)

### BTG_ID
- **Type**: Integer (Discord Snowflake)
- **Required**: Yes
- **Description**: The Discord server ID for the BTG server. Used to sync slash commands to this specific guild.
- **Example**: `BTG_ID=123456789012345678`
- **How to get**: Right-click on the server name in Discord → Copy Server ID (requires Developer Mode enabled)

## Bot Permissions & Access Control

### POSTMAN_ID
- **Type**: Integer (Discord Snowflake)
- **Required**: Yes
- **Description**: The Discord user ID of the bot owner (Postman67). This user has full administrative access to all bot commands regardless of roles.
- **Example**: `POSTMAN_ID=123456789012345678`
- **How to get**: Right-click on your username in Discord → Copy User ID (requires Developer Mode enabled)

### BOTROLE_ID
- **Type**: Integer (Discord Snowflake)
- **Required**: Yes
- **Description**: The Discord role ID that grants users permission to use bot management commands. Users with this role can create, edit, and manage stall entries.
- **Example**: `BOTROLE_ID=123456789012345678`
- **How to get**: Right-click on the role in Server Settings → Roles → Copy Role ID (requires Developer Mode enabled)

## Database Configuration

### DB_USER
- **Type**: String
- **Required**: Yes
- **Description**: Username for the MariaDB/MySQL database connection. This user should have read/write permissions on the `furryville` database.
- **Example**: `DB_USER=furryville_bot`
- **Security**: Moderate - Should be a dedicated database user with limited permissions

### DB_PASSWORD
- **Type**: String
- **Required**: Yes
- **Description**: Password for the MariaDB/MySQL database user specified in DB_USER.
- **Example**: `DB_PASSWORD=your_secure_password_here`
- **Security**: HIGH - Use a strong, unique password. Never commit this to version control.

### DB_HOST
- **Type**: String
- **Required**: Yes
- **Description**: Hostname or IP address of the MariaDB/MySQL database server.
- **Example**: `DB_HOST=furryville-index.db` or `DB_HOST=localhost` or `DB_HOST=192.168.1.100`
- **Security**: Moderate - Should be accessible only from authorized sources

### DB_DATABASE
- **Type**: String
- **Required**: Yes
- **Description**: Name of the specific database to connect to on the database server.
- **Example**: `DB_DATABASE=furryville`
- **Security**: Low - Database name is not sensitive but should be consistent across environments

## Database Schema Information

The bot connects to a MariaDB database using configurable environment variables:
- **Host**: Configured via `DB_HOST` environment variable
- **Database**: Configured via `DB_DATABASE` environment variable
- **Tables**: Various tables for storing stall information and reviews

## Environment File Example

Create a `.env` file in the root directory with these variables:

```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token_here
FURRYVILLE_ID=123456789012345678
BTG_ID=987654321098765432

# Bot Access Control
POSTMAN_ID=111111111111111111
BOTROLE_ID=222222222222222222

# Database Configuration
DB_USER=your_database_username
DB_PASSWORD=your_secure_database_password
DB_HOST=furryville-index.db
DB_DATABASE=furryville
```

## Security Best Practices

1. **Never commit the `.env` file** to version control
2. **Add `.env` to your `.gitignore` file**
3. **Use strong, unique passwords** for database access
4. **Rotate tokens regularly** especially if they may have been compromised
5. **Limit database user permissions** to only what's needed
6. **Keep Discord tokens secure** - they provide full bot control
7. **Regularly audit** who has access to these environment variables

## Troubleshooting

- **Bot won't start**: Check that DISCORD_TOKEN is correct and valid
- **Commands not syncing**: Verify FURRYVILLE_ID and BTG_ID are correct server IDs
- **Permission errors**: Ensure POSTMAN_ID and BOTROLE_ID are set correctly
- **Database errors**: Verify DB_USER, DB_PASSWORD, DB_HOST, and DB_DATABASE, and ensure database is accessible
