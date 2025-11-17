"""Main entry point for Jambot."""
import sys
import discord
from src.config import Config
from src.logger import logger
from src.bot import JamBot


def main():
    """Run the Jambot Discord bot."""
    try:
        # Validate configuration
        logger.info("Validating configuration...")
        Config.validate()
        logger.info("Configuration validated successfully")

        # Create and run bot
        logger.info("Starting Jambot...")
        bot = JamBot()

        logger.info("Attempting to connect to Discord...")
        logger.info(f"Using bot token: {Config.DISCORD_BOT_TOKEN[:20]}...")

        bot.run(Config.DISCORD_BOT_TOKEN, log_handler=None)  # We handle logging ourselves

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except discord.LoginFailure as e:
        logger.error(f"Discord login failed - invalid bot token: {e}")
        sys.exit(1)
    except discord.HTTPException as e:
        logger.error(f"Discord HTTP error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
