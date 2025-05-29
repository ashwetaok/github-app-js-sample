# Real-Time OI (Open Interest) Tracker

This Python script tracks real-time Open Interest (OI) data for NIFTY 50 and BANKNIFTY options from the National Stock Exchange (NSE) via the Kite Connect API. It identifies At-The-Money (ATM) strikes and monitors OI changes for several strikes around the ATM for both Call and Put options.

## Features

-   **Kite Connect API Integration**: Securely connect to Zerodha's Kite Connect API.
-   **Automatic Access Token Handling**:
    -   Guides through one-time access token generation if not already configured.
    -   Uses pre-configured access token for subsequent runs.
-   **Dynamic ATM Strike Calculation**: Fetches the Last Traded Price (LTP) of the underlying (e.g., NIFTY 50) to determine the current ATM strike.
-   **Relevant Strike Identification**: Generates a list of option symbols (Calls and Puts) for strikes around the ATM (e.g., ATM +/- 2 strikes).
-   **Historical OI Change Calculation**:
    -   Fetches historical minute-level OI data for the identified option symbols.
    -   Calculates OI changes over configurable time intervals (e.g., last 10, 15, 30 minutes).
-   **Tabular Data Display**: Presents the OI change data in a clear, tabular format using pandas, distinguishing between Call and Put options and highlighting the ATM strike.
-   **Continuous Monitoring**: Runs in a loop, periodically updating and displaying the OI data.
-   **Configurable Parameters**: Key parameters like underlying symbol, expiry details, strike steps, and update frequency can be easily configured within the script.
-   **Logging**: Comprehensive logging for monitoring script execution, API interactions, and potential errors.
-   **Unit Tests**: Basic unit tests for core logic functions.

## Prerequisites

-   Python 3.x
-   A Zerodha Kite Connect developer account with API key and secret.
-   Required Python libraries (install via `pip`):
    -   `kiteconnect`
    -   `pandas`
    -   `requests` (usually a dependency of kiteconnect)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Install dependencies:**
    ```bash
    pip install kiteconnect pandas
    ```

3.  **Configure API Credentials & Parameters in `oi_tracker.py`:**
    Open `oi_tracker.py` and update the following global variables and parameters within the `if __name__ == "__main__":` block:

    *   **API Credentials (Global):**
        ```python
        API_KEY = "YOUR_API_KEY"
        API_SECRET = "YOUR_API_SECRET"
        ACCESS_TOKEN = "YOUR_ACCESS_TOKEN" # Optional: Leave as "YOUR_ACCESS_TOKEN" for first run
        ```
        *   Get `API_KEY` and `API_SECRET` from your [Kite Connect Developer Dashboard](https://developers.kite.trade).
        *   `ACCESS_TOKEN` will be generated on the first run if not provided. You'll be prompted to log in via a URL and enter a `request_token`. The script will then generate and print the `ACCESS_TOKEN`. **It is highly recommended to copy this generated `ACCESS_TOKEN` back into the `ACCESS_TOKEN` variable in the script for future runs to avoid repeated manual logins.**

    *   **Operational Parameters (within `if __name__ == "__main__":`)**
        ```python
        UNDERLYING_SYMBOL = "NIFTY 50"  # e.g., "NIFTY 50", "BANKNIFTY"
        # EXCHANGE for the underlying symbol (e.g., "NSE" for NIFTY 50, "INDICES" if that's what your Kite app uses for LTP of Nifty Index)
        EXCHANGE = "NSE" 
        OPTIONS_EXCHANGE = "NFO" # Exchange for fetching options instruments
        
        # IMPORTANT: Verify and set CURRENT_EXPIRY_DETAILS_STR
        # This string is crucial for generating correct option trading symbols.
        # Its format depends on the instrument and Kite's naming convention. Examples:
        # - For NIFTY/BANKNIFTY weekly options, it might be "YYMDD" (e.g., "24620" for 20th June 2024).
        # - Or "YYMMM" (e.g., "24JUN" for June 2024 monthly expiry).
        # Check Kite's instrument list or contract notes for the exact format.
        CURRENT_EXPIRY_DETAILS_STR = "24620" # Example: Needs verification!
        
        STRIKE_STEP = 50          # 50 for NIFTY, 100 for BANKNIFTY
        COUNT_AROUND_ATM = 2      # Number of strikes above and below ATM to track (e.g., 2 means ATM-2, ATM-1, ATM, ATM+1, ATM+2)
        LOOP_DELAY_SECONDS = 60   # Time in seconds between data refresh cycles
        ```

## Running the Script

Once configured, run the script from your terminal:

```bash
python oi_tracker.py
```

-   **First Run**: If `ACCESS_TOKEN` is not configured, the script will print a Kite login URL. Open it in your browser, log in, and you'll be redirected to a URL containing a `request_token`. Copy this `request_token` and paste it into the script when prompted. The script will then generate and print your `ACCESS_TOKEN`. Copy this token back into the `ACCESS_TOKEN` variable in `oi_tracker.py` to avoid this process in the future.
-   **Subsequent Runs**: If `ACCESS_TOKEN` is correctly configured, the script will connect directly and start tracking OI.

The script will continuously fetch and display OI change data for the specified strikes in a tabular format. Press `Ctrl+C` to stop the script.

## How it Works

1.  **Authentication**: Connects to Kite API using the provided credentials.
2.  **Instrument Loading**: Fetches the list of all available NFO (Futures and Options) instruments once to map trading symbols to instrument tokens.
3.  **ATM Strike Determination**: Periodically fetches the LTP of the `UNDERLYING_SYMBOL` (e.g., NIFTY 50) to find the current At-The-Money (ATM) strike price.
4.  **Option Chain Selection**: Generates trading symbols for a predefined number of Call and Put option strikes around the ATM strike (e.g., 2 ITM, ATM, 2 OTM).
5.  **OI Data Fetching**: For each selected option symbol:
    -   Resolves the trading symbol to its `instrument_token`.
    -   Fetches historical minute-level data (including OI) for the recent past (e.g., last 30-40 minutes).
6.  **OI Change Calculation**: Compares the latest OI with OI at previous time points (e.g., 10, 15, 30 minutes ago) to determine changes.
7.  **Display**: Formats and prints the strike-wise OI change data for Calls and Puts in separate tables.
8.  **Loop**: Repeats steps 3-7 after a configured delay.

## Unit Tests

Basic unit tests are provided in `test_oi_tracker.py`. To run them:

```bash
python -m unittest test_oi_tracker.py
```

## Disclaimer

-   This script is for educational and informational purposes only.
-   It is NOT financial advice.
-   Trading in the stock market involves substantial risk. Always do your own research and consult with a qualified financial advisor before making any trading decisions.
-   The accuracy and availability of data depend on the Kite Connect API and market conditions.
-   The script's symbol generation and strike extraction logic relies on common patterns; ensure `CURRENT_EXPIRY_DETAILS_STR` is correctly configured for your specific needs.
```
