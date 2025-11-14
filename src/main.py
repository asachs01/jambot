"""Main entry point for Jambot."""
import sys
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
        bot.run(Config.DISCORD_BOT_TOKEN, log_handler=None)  # We handle logging ourselves

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
