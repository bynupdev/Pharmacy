#!/usr/bin/env python
"""
Simple script to import SQLite data to Neon PostgreSQL
Run: python import_to_neon.py
"""

import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# SQLite database path
SQLITE_DB = 'db.sqlite3'

# Neon connection string
NEON_URL = os.getenv('DATABASE_URL')

print("=" * 60)
print("IMPORTING SQLITE DATA TO NEON")
print("=" * 60)

# Connect to SQLite
print("\n[1/4] Connecting to SQLite...")
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_conn.row_factory = sqlite3.Row
print("   OK")

# Connect to Neon
print("\n[2/4] Connecting to Neon...")
try:
    pg_conn = psycopg2.connect(NEON_URL)
    pg_conn.autocommit = False
    pg_cursor = pg_conn.cursor()
    print("   OK")
except Exception as e:
    print(f"   ERROR: {e}")
    print("\nMake sure your DATABASE_URL in .env is correct")
    sys.exit(1)

# Tables to import (in correct order for foreign keys)
tables = [
    'accounts_pharmacy',
    'auth_user',
    'accounts_userprofile',
    'inventory_supplier',
    'inventory_drug',
    'inventory_batch',
    'patients_patient',
    'prescriptions_prescription',
    'prescriptions_prescriptionitem',
    'sales_sale',
    'sales_saleitem',
]

print("\n[3/4] Importing data...")

for table in tables:
    try:
        # Get data from SQLite
        cursor = sqlite_conn.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        
        if not rows:
            print(f"   SKIP: {table} (no data)")
            continue
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        
        # Clear existing data in Neon (optional - be careful!)
        pg_cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
        
        # Insert data
        placeholders = ','.join(['%s'] * len(columns))
        insert_sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
        
        for row in rows:
            pg_cursor.execute(insert_sql, tuple(row))
        
        pg_conn.commit()
        print(f"   OK: {table} ({len(rows)} rows)")
        
    except Exception as e:
        print(f"   ERROR: {table} - {str(e)[:100]}")
        pg_conn.rollback()

# Reset sequences
print("\n[4/4] Resetting sequences...")
try:
    pg_cursor.execute("""
        SELECT 'SELECT SETVAL(' || quote_literal(quote_ident(PGT.schemaname) || '.' || quote_ident(PGT.tablename)) || 
               ', COALESCE(MAX(' || quote_ident(C.column_name) || '), 1) ) FROM ' || quote_ident(PGT.schemaname) || '.' || quote_ident(PGT.tablename) || ';'
        FROM pg_tables PGT
        JOIN information_schema.columns C
        ON C.table_name = PGT.tablename AND C.column_name = 'id'
        WHERE PGT.schemaname = 'public'
    """)
    sequence_queries = pg_cursor.fetchall()
    for query in sequence_queries:
        try:
            pg_cursor.execute(query[0])
        except:
            pass
    pg_conn.commit()
    print("   OK")
except Exception as e:
    print(f"   Warning: {e}")

# Close connections
sqlite_conn.close()
pg_cursor.close()
pg_conn.close()

print("\n" + "=" * 60)
print("IMPORT COMPLETE!")
print("=" * 60)
print("\nYour data is now in Neon PostgreSQL")