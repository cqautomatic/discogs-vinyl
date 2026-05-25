#!/bin/bash

# Nightly Discogs Maintenance Script  
# Runs price refresh and materialized views refresh at 1 AM daily
# Sends email notifications only on failure

# Log file location (defined early for error logging)
LOG_FILE="/Users/joeyfoley/cursor_1/discogs_project/logs/nightly_maintenance.log"

# Create logs directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Set the working directory
cd /Users/joeyfoley/cursor_1/discogs_project/apps/postgres/discogs_collection_postgres_lab

# Activate the virtual environment
source discogs/bin/activate

# Verify virtual environment is activated
if [[ "$VIRTUAL_ENV" != *"discogs"* ]]; then
    echo "$(date): ERROR - Virtual environment not activated properly" >> "$LOG_FILE"
    exit 1
fi

# Set up environment (adjust paths as needed)
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

# Load environment variables if you have a .env file
# source /path/to/your/.env

# Set required environment variables (adjust these to your actual values)
export DISCOGS_TOKEN="${DISCOGS_TOKEN}"
export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-5432}"
export PGDATABASE="${PGDATABASE:-discogs_collection}"
export PGUSER="${PGUSER:-postgres}"
export PGPASSWORD="${PGPASSWORD}"

# Email settings for error notifications
EMAIL_TO="joey.foley@gmail.com"
EMAIL_SUBJECT="Discogs Nightly Maintenance Failed"

# Function to send error email
send_error_email() {
    local error_details="$1"
    local timestamp=$(date)
    
    # Check if mail command is available
    if command -v mail >/dev/null 2>&1; then
        echo "Discogs nightly maintenance failed at $timestamp

Error Details:
$error_details

Log file: $LOG_FILE

Please check the system and resolve any issues.

This is an automated message from the Discogs price refresh cron job." | mail -s "$EMAIL_SUBJECT" "$EMAIL_TO"
    elif command -v sendmail >/dev/null 2>&1; then
        {
            echo "To: $EMAIL_TO"
            echo "Subject: $EMAIL_SUBJECT"
            echo ""
            echo "Discogs nightly maintenance failed at $timestamp"
            echo ""
            echo "Error Details:"
            echo "$error_details"
            echo ""
            echo "Log file: $LOG_FILE"
            echo ""
            echo "Please check the system and resolve any issues."
            echo ""
            echo "This is an automated message from the Discogs price refresh cron job."
        } | sendmail "$EMAIL_TO"
    else
        echo "$(date): ERROR - No mail system available to send error notification" >> "$LOG_FILE"
    fi
}

# Log start time
echo "$(date): Starting nightly maintenance (price refresh + materialized views)" >> "$LOG_FILE"

# Run the price refresh
echo "$(date): Starting price refresh..." >> "$LOG_FILE"
python3 discogs_downloader.py --refresh-prices >> "$LOG_FILE" 2>&1
PRICE_EXIT_CODE=$?

# Log price refresh completion
if [ $PRICE_EXIT_CODE -eq 0 ]; then
    echo "$(date): Price refresh completed successfully" >> "$LOG_FILE"
else
    echo "$(date): Price refresh failed with exit code $PRICE_EXIT_CODE" >> "$LOG_FILE"
fi

# Run materialized views refresh
echo "$(date): Starting materialized views refresh..." >> "$LOG_FILE"
python3 refresh_views.py --quiet >> "$LOG_FILE" 2>&1
VIEWS_EXIT_CODE=$?

# Log views refresh completion
if [ $VIEWS_EXIT_CODE -eq 0 ]; then
    echo "$(date): Materialized views refresh completed successfully" >> "$LOG_FILE"
else
    echo "$(date): Materialized views refresh failed with exit code $VIEWS_EXIT_CODE" >> "$LOG_FILE"
fi

# Overall completion status
if [ $PRICE_EXIT_CODE -eq 0 ] && [ $VIEWS_EXIT_CODE -eq 0 ]; then
    echo "$(date): Nightly maintenance completed successfully" >> "$LOG_FILE"
else
    ERROR_MSG="Nightly maintenance completed with errors (Price exit code: $PRICE_EXIT_CODE, Views exit code: $VIEWS_EXIT_CODE)"
    echo "$(date): $ERROR_MSG" >> "$LOG_FILE"
    
    # Send error email
    DETAILED_ERROR="Price Refresh Exit Code: $PRICE_EXIT_CODE
Materialized Views Exit Code: $VIEWS_EXIT_CODE

Recent log entries:
$(tail -20 "$LOG_FILE")"
    
    send_error_email "$DETAILED_ERROR"
fi

echo "----------------------------------------" >> "$LOG_FILE"