from dotenv import load_dotenv
import os
from cryptoagent.main import CryptoAgent
import json

# Load environment variables
load_dotenv()

def main():
    # Initialize CryptoAgent without the AI part
    crypto_agent = CryptoAgent(None)  # We don't need the AI agent for just fetching data

    # Fetch only BTC data
    coins = ["btc"]
    result = crypto_agent.run_multiple_coins(coins, real_time=True)
    
    # Parse and display the data nicely
    data = json.loads(result)[0]['data']
    
    # Display key metrics
    print("\n=== Bitcoin Real-Time Data ===")
    print(f"Current Price: ${data['current_price']:,.2f}")
    print(f"24h High: ${data['high_24h']:,.2f}")
    print(f"24h Low: ${data['low_24h']:,.2f}")
    print(f"24h Change: {data['price_change_percentage_24h']:,.2f}%")
    print(f"Market Cap: ${data['market_cap']:,.2f}")
    print(f"Trading Volume: ${data['total_volume']:,.2f}")
    print(f"Last Updated: {data['last_updated']}")

if __name__ == "__main__":
    main()
