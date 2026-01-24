"""Test configuration for Jambot."""
import os
import sys

# Set LOG_FILE to avoid Docker path issues during testing
os.environ.setdefault('LOG_FILE', '/tmp/jambot_test.log')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
