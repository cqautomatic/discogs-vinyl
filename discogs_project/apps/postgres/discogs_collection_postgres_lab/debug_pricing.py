#!/usr/bin/env python3
"""Debug script to check wantlist pricing data."""

import sys
import os
sys.path.append('.')

from core.database import PostgreSQLConnection
import pandas as pd

def main():
    db = PostgreSQLConnection()
    
    print("=== CHECKING WANTLIST DATA ===")
    try:
        wantlist_query = "SELECT COUNT(*) FROM wantlist;"
        wantlist_count = db.execute_query(wantlist_query)
        if wantlist_count:
            count = wantlist_count[0][0]
            print(f"Wantlist table has {count} rows")
            
            if count > 0:
                sample_query = "SELECT discogs_release_id, title FROM wantlist LIMIT 5;"
                sample_result = db.execute_query(sample_query)
                if sample_result:
                    print("Sample wantlist items:")
                    for row in sample_result:
                        print(f"  ID: {row[0]}, Title: {row[1][:50]}...")
        else:
            print("Could not check wantlist table")
    except Exception as e:
        print(f"Error checking wantlist: {e}")
    
    print("\n=== CHECKING RELEASE_PRICES DATA ===")
    prices_query = "SELECT discogs_release_id, lowest_price, currency FROM release_prices WHERE lowest_price IS NOT NULL LIMIT 5;"
    prices_result = db.execute_query(prices_query)
    if prices_result and len(prices_result) > 0:
        for row in prices_result:
            print(f"Price ID: {row[0]}, Price: {row[1]}, Currency: {row[2]}")
    else:
        print("No pricing data found")
        # Check if table exists and has data
        price_check = db.execute_query("SELECT COUNT(*) FROM release_prices;")
        if price_check:
            print(f"Release_prices table has {price_check[0][0]} rows")
        price_check_with_prices = db.execute_query("SELECT COUNT(*) FROM release_prices WHERE lowest_price IS NOT NULL;")
        if price_check_with_prices:
            print(f"Release_prices table has {price_check_with_prices[0][0]} rows with prices")
    
    print("\n=== TESTING EXACT JOIN QUERY FROM load_wantlist_items ===")
    join_query = """
    SELECT 
        w.discogs_release_id,
        w.title,
        w.artist,
        w.year,
        w.label,
        w.format,
        w.genres,
        w.styles,
        w.notes,
        w.rating,
        w.added,
        rp.lowest_price,
        rp.currency,
        rp.num_for_sale,
        rp.availability,
        rp.last_seen as price_last_seen
    FROM wantlist w
    LEFT JOIN release_prices rp ON w.discogs_release_id = rp.discogs_release_id
    ORDER BY 
        CASE WHEN rp.availability = true THEN 0 ELSE 1 END,
        rp.lowest_price ASC NULLS LAST,
        w.added DESC
    LIMIT 5
    """
    
    join_result = db.execute_query(join_query)
    if join_result:
        columns = ['discogs_release_id', 'title', 'artist', 'year', 'label', 'format', 
                  'genres', 'styles', 'notes', 'rating', 'added', 'lowest_price', 
                  'currency', 'num_for_sale', 'availability', 'price_last_seen']
        
        df = pd.DataFrame(join_result, columns=columns)
        print("JOIN Query Results:")
        for idx, row in df.iterrows():
            title = row['title'][:30] if row['title'] else 'N/A'
            price = row['lowest_price'] if pd.notna(row['lowest_price']) else 'NULL'
            currency = row['currency'] if pd.notna(row['currency']) else 'NULL'
            available = row['availability'] if pd.notna(row['availability']) else 'NULL'
            print(f"  Title: {title}..., Price: {price}, Currency: {currency}, Available: {available}")
    else:
        print("No join results found")
    
    db.close()

if __name__ == "__main__":
    main()