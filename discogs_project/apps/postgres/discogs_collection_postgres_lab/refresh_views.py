#!/usr/bin/env python3
"""
Standalone script to refresh materialized views.
Can be used for scheduled refreshes or manual updates.
"""

import sys
import argparse
from pathlib import Path

# Add the app directory to path so we can import modules
app_dir = Path(__file__).parent
sys.path.append(str(app_dir))

from core.database import PostgreSQLConnection
from data.performance import refresh_materialized_views

def main():
    """Main function to refresh materialized views."""
    parser = argparse.ArgumentParser(description="Refresh materialized views")
    parser.add_argument("--quiet", "-q", action="store_true", 
                       help="Suppress output messages")
    args = parser.parse_args()
    
    try:
        # Connect to database
        db_conn = PostgreSQLConnection()
        
        if not db_conn.connection:
            if not args.quiet:
                print("ERROR: Cannot connect to database")
            sys.exit(1)
        
        if not args.quiet:
            print("Refreshing materialized views...")
        
        # Refresh views
        success = refresh_materialized_views(db_conn)
        
        if success:
            if not args.quiet:
                print("✅ Materialized views refreshed successfully!")
            sys.exit(0)
        else:
            if not args.quiet:
                print("❌ Failed to refresh materialized views")
            sys.exit(1)
            
    except Exception as e:
        if not args.quiet:
            print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

