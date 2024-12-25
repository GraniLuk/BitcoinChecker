import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_kucoin_credentials():
    return {
        'api_key': os.getenv('KUCOIN_API_KEY'),
        'api_secret': os.getenv('KUCOIN_API_SECRET'),
        'api_passphrase': os.getenv('KUCOIN_API_PASSPHRASE')
    }
