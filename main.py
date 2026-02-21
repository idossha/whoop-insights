#!/usr/bin/env python3
import argparse
from datetime import datetime
import sys
import os

from src.whoop_sync.config import config
from src.whoop_sync.sync import WhoopSync


def main():
    parser = argparse.ArgumentParser(
        description="Sync Whoop data to local SQLite database"
    )
    parser.add_argument(
        "command",
        choices=["auth", "sync", "stats", "status", "reauth"],
        help="Command to run",
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
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Auth timeout in seconds (default: 300)",
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
            if sync.auth.load_tokens() and sync.auth.is_authenticated():
                print("Already authenticated. Checking if tokens are valid...")
                if sync.auth.refresh_access_token():
                    print("Tokens are valid and have been refreshed.")
                    return

            print("Starting authentication flow...")
            if sync.auth.authorize(timeout=args.timeout):
                print("\nAuthentication successful! You can now run sync.")
            else:
                print("\nAuthentication failed!")
                sys.exit(1)

        elif args.command == "reauth":
            print("Clearing existing tokens and starting fresh authentication...")
            sync.auth.clear_tokens()
            if sync.auth.authorize(timeout=args.timeout):
                print("\nRe-authentication successful! You can now run sync.")
            else:
                print("\nRe-authentication failed!")
                sys.exit(1)

        elif args.command == "status":
            print("Authentication Status:")
            print(f"  Tokens file: {config.tokens_file}")
            if sync.auth.load_tokens():
                print(
                    f"  Has access token: {'Yes' if sync.auth.access_token else 'No'}"
                )
                print(
                    f"  Has refresh token: {'Yes' if sync.auth.refresh_token else 'No'}"
                )
                if sync.auth.expires_at:
                    from datetime import datetime as dt

                    expires = dt.fromtimestamp(sync.auth.expires_at)
                    expired = sync.auth.is_token_expired()
                    print(f"  Token expires: {expires}")
                    print(f"  Token expired: {'Yes' if expired else 'No'}")

                if sync.auth.refresh_token:
                    print("\nTesting token refresh...")
                    if sync.auth.refresh_access_token():
                        print("  Token refresh: SUCCESS")
                    else:
                        print("  Token refresh: FAILED - Need to re-authenticate")
                        print(
                            "  Run: docker exec whoop-dashboard python main.py reauth"
                        )
            else:
                print("  No tokens found. Run 'auth' command first.")
                print("  Run: docker exec whoop-dashboard python main.py auth")

        elif args.command == "sync":
            if not sync.auth.load_tokens():
                print("No tokens found. Run authentication first:")
                print("  docker exec whoop-dashboard python main.py auth")
                sys.exit(1)

            if not sync.auth.is_authenticated():
                print("No valid tokens. Run authentication first:")
                print("  docker exec whoop-dashboard python main.py auth")
                sys.exit(1)

            print("Authenticating...")
            if not sync.authenticate():
                print("Authentication failed. Token may be expired or revoked.")
                print("Run: docker exec whoop-dashboard python main.py reauth")
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
