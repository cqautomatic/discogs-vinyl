#!/usr/bin/env python3
"""
Nightly Discogs price refresh script for cron job execution.
"""

import os
import sys
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parents[1] / 'apps' / 'postgres' / 'discogs_collection_postgres_lab'
sys.path.insert(0, str(project_dir))

# Activate virtual environment programmatically
venv_python = project_dir / 'discogs' / 'bin' / 'python'
if venv_python.exists():
    # Use the venv python interpreter
    import subprocess
    import os
    # Set the virtual environment in the current process
    os.environ['VIRTUAL_ENV'] = str(project_dir / 'discogs')
    os.environ['PATH'] = f"{project_dir / 'discogs' / 'bin'}:{os.environ.get('PATH', '')}"

# Set up logging
log_dir = Path(__file__).resolve().parents[1] / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / 'nightly_price_refresh.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def send_error_email(error_message: str, log_file: Path):
    """Send error notification email."""
    try:
        # Email configuration - modify these as needed
        EMAIL_TO = "joey.foley@gmail.com"
        EMAIL_SUBJECT = "Discogs Nightly Maintenance Failed"
        
        # Try to use system mail command first
        import subprocess
        
        # Get recent log entries
        try:
            log_tail = subprocess.check_output(['tail', '-20', str(log_file)], 
                                             universal_newlines=True)
        except:
            log_tail = "Could not read log file"
        
        email_body = f"""Discogs nightly maintenance failed at {datetime.now()}

Error Details:
{error_message}

Recent log entries:
{log_tail}

Log file: {log_file}

Please check the system and resolve any issues.

This is an automated message from the Discogs price refresh cron job."""

        # Try to send using mail command
        try:
            subprocess.run(['mail', '-s', EMAIL_SUBJECT, EMAIL_TO], 
                          input=email_body, text=True, check=True)
            logger.info("Error notification email sent successfully")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Could not send email using mail command")
            
    except Exception as e:
        logger.error(f"Failed to send error email: {e}")

def main():
    """Run the nightly maintenance (price refresh + materialized views)."""
    try:
        logger.info("Starting nightly maintenance (price refresh + materialized views)")
        
        # Change to the correct directory
        os.chdir(project_dir)
        
        # Run price refresh
        logger.info("Starting price refresh...")
        from discogs_downloader import DiscogsCollectionDownloader
        DiscogsCollectionDownloader.refresh_prices_via_script(batch_limit=None)
        logger.info("Price refresh completed successfully")
        
        # Run materialized views refresh
        logger.info("Starting materialized views refresh...")
        from core.database import PostgreSQLConnection
        from data.performance import refresh_materialized_views
        
        db_conn = PostgreSQLConnection()
        if not db_conn.connection:
            raise RuntimeError("Cannot connect to database for materialized views refresh")
        
        success = refresh_materialized_views(db_conn)
        if not success:
            raise RuntimeError("Failed to refresh materialized views")
        
        logger.info("Materialized views refresh completed successfully")
        logger.info("Nightly maintenance completed successfully")
        
    except Exception as e:
        error_msg = f"Nightly maintenance failed: {e}"
        logger.error(error_msg, exc_info=True)
        
        # Send error email
        send_error_email(error_msg, log_file)
        sys.exit(1)

if __name__ == "__main__":
    main()