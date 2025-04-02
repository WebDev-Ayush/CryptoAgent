from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
import os
from cryptoagent.main import CryptoAgent
import json
from datetime import datetime

app = Flask(__name__)
load_dotenv()

def get_bitcoin_data():
    crypto_agent = CryptoAgent(None)
    coins = ["btc"]
    result = crypto_agent.run_multiple_coins(coins, real_time=True)
    data = json.loads(result)[0]['data']
    return data

@app.route('/')
def index():
    data = get_bitcoin_data()
    return render_template('index.html', data=data)

@app.route('/api/bitcoin')
def bitcoin_data():
    data = get_bitcoin_data()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=3000) 