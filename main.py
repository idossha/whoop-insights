#!/usr/bin/env python3
import argparse
from datetime import datetime
import sys

from src.whoop_sync.config import config
from src.whoop_sync.sync import WhoopSync


def main():
    parser = argparse.ArgumentParser(
        description="Sync Whoop data to local SQLite database"
    )
    parser.add_argument(
        "command", choices=["auth", "sync", "stats"], help="Command to run"
    )
    parser.add_argument(
        "--full", action="store_true", help="Full sync instead of incremental"
    )
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--types",
        type=str,
        help="Data types to sync (comma-separated: cycles,recoveries,sleeps,workouts)",
    )

    args = parser.parse_args()

    if not config.validate():
        print("Error: WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET must be set")
        print("\n1. Go to https://developer-dashboard.whoop.com/")
        print("2. Create a new application")
        print("3. Set the redirect URI to: http://localhost:8080/callback")
        print("4. Copy the Client ID and Secret to your .env file")
        sys.exit(1)

    sync = WhoopSync()

    try:
        if args.command == "auth":
            print("Starting authentication flow...")
            if sync.authenticate():
                print("Authentication successful!")
            else:
                print("Authentication failed!")
                sys.exit(1)

        elif args.command == "sync":
            if not sync.authenticate():
                print("Authentication required. Run 'whoop_sync auth' first.")
                sys.exit(1)

            start = None
            end = None

            if args.start:
                start = datetime.strptime(args.start, "%Y-%m-%d")
            if args.end:
                end = datetime.strptime(args.end, "%Y-%m-%d")

            if args.types:
                types = args.types.split(",")
                if "cycles" in types:
                    sync.sync_cycles(start=start, end=end, full_sync=args.full)
                if "recoveries" in types:
                    sync.sync_recoveries(start=start, end=end, full_sync=args.full)
                if "sleeps" in types:
                    sync.sync_sleeps(start=start, end=end, full_sync=args.full)
                if "workouts" in types:
                    sync.sync_workouts(start=start, end=end, full_sync=args.full)
            else:
                sync.sync_all(full_sync=args.full, start=start, end=end)

            print("\nSync complete!")

        elif args.command == "stats":
            stats = sync.db.get_stats()
            print("Database statistics:")
            for table, count in stats.items():
                print(f"  {table}: {count} records")

    finally:
        sync.close()


if __name__ == "__main__":
    main()
