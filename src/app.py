"""Combined application entry point for web server and Discord bot."""
import asyncio
import threading
import os
from src.logger import logger
from src.web_server import run_server
from src.main import main as run_bot

def start_web_server():
    """Start the Flask web server in a separate thread."""
    port = int(os.getenv('PORT', 8080))  # App Platform uses PORT env var
    logger.info(f"Starting web server on port {port}")
    run_server(host='0.0.0.0', port=port)

def main():
    """Run both web server and Discord bot."""
    logger.info("Starting Jambot application...")

    # Start web server in background thread
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    logger.info("Web server thread started")

    # Run Discord bot in main thread
    logger.info("Starting Discord bot...")
    run_bot()

if __name__ == '__main__':
    main()
