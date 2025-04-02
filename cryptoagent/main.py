from datetime import datetime
from typing import Dict, List, Union, Protocol, Any, Optional
import os
import uuid
import requests
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from .schema import CryptoAgentSchema, CryptoAgentSchemaLog


class AgentProtocol(Protocol):
    """Protocol for agents that can be used with CryptoAgent."""
    def run(self, input_data: str) -> str:
        """Run the agent on input data."""
        ...


class TokenUsage(BaseModel):
    """
    Schema for logging token usage by the LLM.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class CryptoAgent:
    """
    A class for analyzing cryptocurrency data using an LLM agent.
    """

    def __init__(
        self,
        agent: AgentProtocol,
        autosave: bool = True,
        workspace_folder: str = "workspace",
        log_file_name: str = "crypto_analysis.log"
    ):
        """
        Initialize the CryptoAgent.

        Args:
            agent (AgentProtocol): The agent to use for analysis.
            autosave (bool, optional): Whether to autosave logs. Defaults to True.
            workspace_folder (str, optional): The folder to save logs in. Defaults to "workspace".
            log_file_name (str, optional): The name of the log file. Defaults to "crypto_analysis.log".
        """
        self.agent = agent
        self.autosave = autosave
        self.workspace_folder = workspace_folder
        self.log_file_name = log_file_name

        # Create workspace folder if it doesn't exist
        if self.autosave:
            os.makedirs(self.workspace_folder, exist_ok=True)

        self.logs = CryptoAgentSchemaLog(
            agent_name="crypto-price-agent-01",
            agent_description="Fetches real-time crypto data for a specific coin",
            logs=[]
        )
        
    def run_agent(self, input_data: str) -> str:
        """
        Run the agent with the given input.

        Args:
            input_data (str): The input data for the agent.

        Returns:
            str: The agent's response.
        """
        try:
            result = self.agent.invoke({"input": input_data})
            return result.get("output", "No output from agent")
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            return f"Error running agent: {str(e)}"
        
    def analyze_crypto(
        self,
        coin_id: str,
        timeframe: str = "24h",
        real_time: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze a cryptocurrency using real-time data.

        Args:
            coin_id (str): The ID of the cryptocurrency to analyze.
            timeframe (str, optional): The timeframe to analyze. Defaults to "24h".
            real_time (bool, optional): Whether to use real-time data. Defaults to True.

        Returns:
            Dict[str, Any]: The analysis results.
        """
        # Get crypto data
        crypto_data = self.get_crypto_data_coingecko(coin_id)
        if isinstance(crypto_data, str):
            return {"error": crypto_data}

        # Format the data for analysis
        crypto_info = json.dumps(crypto_data, indent=2)

        # Create the prompt
        prompt = f"""Here is the live data for {crypto_data.get('name', coin_id)}:

{crypto_info}

Please provide a detailed analysis for {crypto_data.get('name', coin_id)} over the {timeframe} timeframe. Include:
1. Current market status
2. Price trends and momentum
3. Key metrics analysis (market cap, volume, etc.)
4. Notable events or factors affecting the price
5. Technical indicators if relevant
6. Potential risks and opportunities"""

        # Get the analysis
        try:
            analysis = self.run_agent(prompt)
            
            # Create the log entry
            log_entry = CryptoAgentSchema(
                timestamp=datetime.now().isoformat(),
                coin_id=coin_id,
                timeframe=timeframe,
                real_time=real_time,
                data=crypto_data,
                analysis=analysis
            )
            
            # Add to logs
            self.logs.logs.append(log_entry)
            
            # Save logs if autosave is enabled
            if self.autosave:
                self.save_logs()
            
            return {
                "coin_id": coin_id,
                "timeframe": timeframe,
                "analysis": analysis,
                "data": crypto_data
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {coin_id}: {e}")
            return {"error": str(e)}

    def get_crypto_data_coingecko(
        self, coin_id: str
    ) -> Union[Dict, str]:
        """
        Fetch crypto data from CoinGecko.

        Args:
        - coin_id (str): The ID of the coin to fetch data for.

        Returns:
        - Union[Dict, str]: The fetched crypto data or an error message.
        """
        # Map common symbols to CoinGecko IDs
        coin_map = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "usdt": "tether",
            "bnb": "binancecoin",
            "sol": "solana",
            "xrp": "ripple",
            "ada": "cardano",
            "doge": "dogecoin",
            "avax": "avalanche-2",
            "dot": "polkadot",
        }
        
        # Get the correct coin ID
        coingecko_id = coin_map.get(coin_id, coin_id)
        
        try:
            params = {"vs_currency": "usd", "ids": coingecko_id}
            response = requests.get("https://api.coingecko.com/api/v3/coins/markets", params=params)
            response.raise_for_status()
            data = response.json()
            if data:
                return data[0]  # Return the first result
            else:
                logger.warning(
                    f"No data found for {coin_id} on CoinGecko."
                )
                return {
                    "error": f"No data found for {coin_id} on CoinGecko."
                }
        except requests.RequestException as e:
            logger.error(
                f"Error fetching data from CoinGecko for {coin_id}: {e}"
            )
            return {"error": str(e)}

    def get_crypto_data(self, coin_id: str) -> Dict:
        """
        Fetch crypto data from CoinGecko.

        Args:
        - coin_id (str): The ID of the coin to fetch data for.

        Returns:
        - Dict: The fetched crypto data.
        """
        logger.info(f"Fetching data for {coin_id} from CoinGecko.")
        data = self.get_crypto_data_coingecko(coin_id)
        return data

    def fetch_and_summarize(
        self,
        coin_id: str,
        task: Optional[str] = None,
        real_time: bool = True,
    ) -> Dict[str, Any]:
        """
        Fetch and summarize data for a single coin.

        Args:
            coin_id (str): The ID of the coin to analyze.
            task (Optional[str]): Optional task description.
            real_time (bool, optional): Whether to use real-time data. Defaults to True.

        Returns:
            Dict[str, Any]: The analysis results.
        """
        logger.info(f"Summarizing data for {coin_id}.")
        
        try:
            # Get crypto data
            crypto_data = self.get_crypto_data_coingecko(coin_id)
            if isinstance(crypto_data, str):
                return {"error": crypto_data}

            # Format the data for analysis
            crypto_info = json.dumps(crypto_data, indent=2)

            # Create the prompt
            prompt = f"""Here is the live data for {crypto_data.get('name', coin_id)}:

{crypto_info}

Please provide a detailed analysis for {crypto_data.get('name', coin_id)} over the 24h timeframe. Include:
1. Current market status
2. Price trends and momentum
3. Key metrics analysis (market cap, volume, etc.)
4. Notable events or factors affecting the price
5. Technical indicators if relevant
6. Potential risks and opportunities"""

            if task:
                prompt += f"\n\nAdditional task: {task}"

            # Get the analysis
            analysis = self.run_agent(prompt)
            
            # Create the log entry
            log_entry = CryptoAgentSchema(
                timestamp=datetime.now().isoformat(),
                coin_id=coin_id,
                timeframe="24h",
                real_time=real_time,
                data=crypto_data,
                analysis=analysis
            )
            
            # Add to logs
            self.logs.logs.append(log_entry)
            
            return log_entry.model_dump()
            
        except Exception as e:
            logger.error(f"Error analyzing {coin_id}: {e}")
            return {"error": str(e)}

    def save_logs(self) -> None:
        """Save the logs to a file."""
        try:
            # Create workspace folder if it doesn't exist
            os.makedirs(self.workspace_folder, exist_ok=True)
            
            # Save logs to file
            log_path = os.path.join(self.workspace_folder, self.log_file_name)
            with open(log_path, "w") as f:
                json.dump(self.logs.model_dump(), f, indent=2)
            
            logger.info(f"Logs saved to {log_path}")
        except Exception as e:
            logger.error(f"Error saving logs: {e}")

    def run_multiple_coins(
        self,
        coin_ids: List[str],
        task: Optional[str] = None,
        real_time: bool = True,
    ) -> str:
        """
        Run analysis on multiple coins in parallel.

        Args:
            coin_ids (List[str]): List of coin IDs to analyze.
            task (Optional[str]): Optional task description.
            real_time (bool, optional): Whether to use real-time data. Defaults to True.

        Returns:
            str: JSON string containing the summaries.
        """
        summaries = []
        errors = []

        with ThreadPoolExecutor() as executor:
            future_to_coin = {
                executor.submit(self.fetch_and_summarize, coin_id, task, real_time): coin_id
                for coin_id in coin_ids
            }

            for future in as_completed(future_to_coin):
                coin_id = future_to_coin[future]
                try:
                    result = future.result()
                    if "error" in result:
                        error_summary = CryptoAgentSchema(
                            timestamp=datetime.now().isoformat(),
                            coin_id=coin_id,
                            timeframe="24h",
                            real_time=real_time,
                            data={},
                            analysis=f"Error analyzing {coin_id}: {result['error']}"
                        )
                        errors.append(error_summary.model_dump())
                    else:
                        summaries.append(result)
                except Exception as e:
                    logger.error(f"Error summarizing {coin_id}: {e}")
                    error_summary = CryptoAgentSchema(
                        timestamp=datetime.now().isoformat(),
                        coin_id=coin_id,
                        timeframe="24h",
                        real_time=real_time,
                        data={},
                        analysis=f"Error analyzing {coin_id}: {str(e)}"
                    )
                    errors.append(error_summary.model_dump())

        # Combine summaries and errors
        all_results = summaries + errors

        # Save logs if autosave is enabled
        if self.autosave:
            self.save_logs()

        return json.dumps(all_results, indent=2)
