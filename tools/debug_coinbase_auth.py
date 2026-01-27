#!/usr/bin/env python3
"""Debug Coinbase JWT authentication and credential verification.

This script will:
- Generate a JWT token using the configured env vars
- Print unverified JWT header and claims for inspection
- Call verify_credentials() and print the result

Usage:
    PYTHONPATH=$PWD python3 tools/debug_coinbase_auth.py
"""
import os
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from multi_broker_phoenix.brokers.coinbase_safe_connector import CoinbaseSafeConnector

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger('debug_coinbase_auth')


def main():
    logger.info('Starting Coinbase auth debug')

    # Try to load the canonical .env if present (simple parser, avoids extra deps)
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        logger.info(f"Loading environment from {env_path}")
        for line in env_path.read_text(encoding='utf-8', errors='ignore').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k.strip(), v)

    # Ensure env provides vars
    api_key = os.getenv('COINBASE_API_KEY')
    api_secret = os.getenv('COINBASE_API_SECRET')
    secret_file = os.getenv('COINBASE_API_SECRET_FILE')

    logger.info(f"COINBASE_API_KEY present: {bool(api_key)}")
    logger.info(f"COINBASE_API_SECRET present: {bool(api_secret)}")
    logger.info(f"COINBASE_API_SECRET_FILE present: {bool(secret_file)}")

    conn = CoinbaseSafeConnector(paper_mode=False)

    # Generate token and print details
    try:
        token = conn._generate_jwt_token()
        print('\n=== JWT TOKEN (truncated) ===')
        print(token[:200] + '...' if len(token) > 200 else token)
        print('=== End Token ===\n')

        # Print unverified header and claims
        try:
            import jwt
            header = jwt.get_unverified_header(token)
            claims = jwt.decode(token, options={"verify_signature": False})
            print('Unverified header:', header)
            print('Unverified claims:', claims)
        except Exception as e:
            logger.warning(f'Could not decode token for inspection: {e}')

    except Exception as e:
        logger.error(f'JWT generation failed: {e}')
        return 1

    # If an account UUID is provided, attempt a focused GET /accounts/{account_uuid}
    account_uuid = os.getenv('COINBASE_ACCOUNT_UUID')
    if account_uuid:
        logger.info(f"Attempting focused account fetch for {account_uuid}")
        account_res = conn.get_account(account_uuid)
        print('\n=== get_account() result ===')
        print(account_res)
        print('=== End get_account result ===\n')
        if not account_res.get('success'):
            logger.warning('get_account failed; continuing to run verify_credentials for broader check')

    # Now run verify_credentials which makes a read-only authenticated call
    result = conn.verify_credentials()
    print('\n=== verify_credentials() result ===')
    for k, v in result.items():
        print(f"{k}: {v}")
    print('=== End verify result ===\n')

    if not result.get('success'):
        logger.error('Credential verification failed - inspect logs above and verify .env formatting')
        # Provide quick tips
        logger.info('Tips:')
        logger.info(" - Ensure COINBASE_API_SECRET is either set without surrounding quotes or set via COINBASE_API_SECRET_FILE path")
        logger.info(" - If using .env with literal newlines, consider using '\\n' escapes or COINBASE_API_SECRET_FILE")
        logger.info(" - Verify COINBASE_API_KEY is the full path (organizations/.../apiKeys/...) and has proper permissions")
        return 2

    logger.info('Credentials verified successfully')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())