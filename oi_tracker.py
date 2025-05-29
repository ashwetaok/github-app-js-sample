#!/usr/bin/env python3

# This script is an Open Interest (OI) tracker for futures and options contracts.
# It uses the Kite Connect API to fetch live market data and analyze OI changes.
# The script is intended for educational purposes and should not be used for live trading without thorough testing and understanding.

# Kite Connect API credentials
# To get your API_KEY and API_SECRET, you need to register for a Kite Connect developer account at https://kite.trade/.
# The ACCESS_TOKEN can be generated once using the login flow commented out in the main section below.
# Once generated, you can hardcode it here or store it securely.
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"  # Optional: Can be generated via login flow

# Import necessary libraries
from kiteconnect import KiteConnect
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
import re

# Basic logging setup
# logging.basicConfig(level=logging.INFO) # Moved to main block

# Global variable for NFO instruments data
NFO_INSTRUMENTS_DATA = []

def fetch_nfo_instruments(kite):
    """Fetches all NFO instruments and stores them in the global NFO_INSTRUMENTS_DATA list."""
    global NFO_INSTRUMENTS_DATA
    try:
        NFO_INSTRUMENTS_DATA = kite.instruments('NFO')
        logging.info(f"Successfully fetched {len(NFO_INSTRUMENTS_DATA)} NFO instruments.")
    except Exception as e:
        logging.error(f"Error fetching NFO instruments: {e}")
        NFO_INSTRUMENTS_DATA = [] # Ensure it's an empty list on failure

def get_instrument_token(trading_symbol):
    """Retrieves the instrument token for a given trading symbol from NFO_INSTRUMENTS_DATA."""
    if not NFO_INSTRUMENTS_DATA:
        logging.warning("NFO instruments data is not loaded. Call fetch_nfo_instruments first.")
        return None
    for instrument in NFO_INSTRUMENTS_DATA:
        if instrument['tradingsymbol'] == trading_symbol:
            return instrument['instrument_token']
    logging.warning(f"Instrument token not found for {trading_symbol}.")
    return None

def get_atm_strike(kite, underlying_instrument_symbol="NIFTY 50", exchange="NSE"):
    """
    Fetches the Last Traded Price (LTP) for the underlying instrument and calculates
    the At-The-Money (ATM) strike price.
    """
    try:
        # Construct the full instrument identifier string
        full_instrument_symbol = f"{exchange}:{underlying_instrument_symbol}"
        ltp_data = kite.ltp(full_instrument_symbol)
        
        if ltp_data and full_instrument_symbol in ltp_data and 'last_price' in ltp_data[full_instrument_symbol]:
            ltp = ltp_data[full_instrument_symbol]['last_price']
            # Assuming strike step of 50 for NIFTY 50
            # For other instruments, this logic might need to be more generic
            if "NIFTY 50" in underlying_instrument_symbol or "BANKNIFTY" in underlying_instrument_symbol: # Common indices
                atm_strike = round(ltp / 50) * 50
            else: # Fallback for other instruments, may need adjustment
                atm_strike = round(ltp) 
            logging.info(f"LTP for {underlying_instrument_symbol}: {ltp}, ATM Strike: {atm_strike}")
            return float(atm_strike)
        else:
            logging.error(f"Could not fetch LTP or LTP data malformed for {full_instrument_symbol}: {ltp_data}")
            return None
    except Exception as e:
        logging.error(f"Error fetching LTP for {underlying_instrument_symbol}: {e}")
        return None

def get_relevant_strikes(atm_strike, strike_step, count_around_atm, option_type, expiry_details_str, underlying_prefix="NIFTY"):
    """
    Generates a list of trading symbols for options (CE or PE) around the ATM strike.
    Example: For NIFTY, expiry_details_str could be "YYMDD" like "24620".
    """
    strikes = []
    if atm_strike is None:
        logging.error("ATM strike is None, cannot determine relevant strikes.")
        return []

    for i in range(-count_around_atm, count_around_atm + 1):
        strike_price = atm_strike + (i * strike_step)
        # Simplified trading symbol construction. This is a critical part and
        # highly dependent on the exact naming convention of options on Kite.
        # Format: NIFTYYYMDDSTRIKEPE/CE (e.g. NIFTY2370617000CE for Nifty 06 JUL 2023 17000 CE)
        # The `expiry_details_str` should match this. For simplicity, we might need
        # a helper to get the current week's NIFTY options expiry string.
        # For now, we assume expiry_details_str is correctly formatted (e.g., "23JUL" or "23706" for 6th July 2023)
        # A more robust solution would involve fetching instruments and filtering by expiry.
        # This placeholder will likely need user adjustment for correct symbol generation.
        trading_symbol = f"{underlying_prefix}{expiry_details_str}{int(strike_price)}{option_type}"
        strikes.append(trading_symbol)
    logging.info(f"Relevant {option_type} strikes for ATM {atm_strike} (step {strike_step}, expiry {expiry_details_str}): {strikes}")
    return strikes

def fetch_oi_for_strike(kite, instrument_token, from_datetime, to_datetime, interval="minute"):
    """
    Fetches historical candle data, including Open Interest (OI), for a specific
    instrument token over a given time range and interval.
    """
    try:
        # Ensure from_datetime and to_datetime are datetime objects
        if not isinstance(from_datetime, datetime) or not isinstance(to_datetime, datetime):
            logging.error("from_datetime and to_datetime must be datetime objects.")
            return []

        logging.debug(f"Fetching OI for token {instrument_token} from {from_datetime} to {to_datetime}")
        data = kite.historical_data(instrument_token, from_datetime, to_datetime, interval, oi=True)
        if data:
            logging.debug(f"Successfully fetched {len(data)} records for token {instrument_token}.")
        else:
            logging.debug(f"No data fetched for token {instrument_token} in the given range.")
        return data
    except Exception as e:
        logging.error(f"Error fetching historical OI for token {instrument_token}: {e}")
        return []

def calculate_oi_change(kite, strike_symbol, time_deltas_minutes=[10, 15, 30]):
    """
    Calculates the change in Open Interest (OI) for a given strike symbol over
    specified past time deltas (e.g., 10, 15, 30 minutes).
    """
    instrument_token = get_instrument_token(strike_symbol)
    if not instrument_token:
        logging.warning(f"Cannot calculate OI change for {strike_symbol} as token is not found.")
        return {delta: "N/A" for delta in time_deltas_minutes}

    now = datetime.now()
    # Add a buffer (e.g., 5 minutes) to the oldest time delta to ensure we capture enough data
    # Also add a small buffer to now_to ensure current candle data is included if available
    oldest_delta = max(time_deltas_minutes)
    from_dt = now - timedelta(minutes=oldest_delta + 5) # 5 min buffer
    to_dt = now + timedelta(minutes=1) # 1 min buffer into future to catch current minute

    historical_data = fetch_oi_for_strike(kite, instrument_token, from_dt, to_dt, interval="minute")

    if not historical_data:
        logging.warning(f"No historical data found for {strike_symbol} (token {instrument_token}) between {from_dt} and {to_dt}.")
        return {delta: "N/A" for delta in time_deltas_minutes}

    # Sort data by date just in case it's not, most recent last
    historical_data.sort(key=lambda x: x['date'])
    
    latest_oi_record = historical_data[-1]
    current_oi = latest_oi_record['oi']
    # logging.info(f"Latest OI for {strike_symbol} at {latest_oi_record['date']} is {current_oi}")


    oi_changes = {}
    for delta_minutes in time_deltas_minutes:
        target_time = now - timedelta(minutes=delta_minutes)
        past_oi_record = None
        
        # Iterate backwards from the second to last record to find the closest record to target_time
        # We want the record at or just before the target_time
        for record in reversed(historical_data): # Check all records
            if record['date'] <= target_time:
                past_oi_record = record
                break # Found the closest record at or before target_time
        
        if past_oi_record:
            past_oi = past_oi_record['oi']
            oi_changes[delta_minutes] = current_oi - past_oi
            # logging.info(f"OI for {strike_symbol} at {past_oi_record['date']} (approx T-{delta_minutes}m) was {past_oi}. Change: {oi_changes[delta_minutes]}")
        else:
            oi_changes[delta_minutes] = "N/A" # Data not available for this past point
            logging.warning(f"Could not find OI data for {strike_symbol} around T-{delta_minutes}m ({target_time}).")
    
    return oi_changes

def display_tables(call_data_list, put_data_list, atm_strike):
    """
    Displays Call and Put OI change data in formatted tables using pandas.
    Highlights the ATM strike in the tables.
    """
    oi_change_columns_map = {
        10: 'OI Change (10m)',
        15: 'OI Change (15m)',
        30: 'OI Change (30m)'
    }
    # Ensure the order of columns if we select them by these names later
    ordered_display_columns = [oi_change_columns_map[key] for key in sorted(oi_change_columns_map.keys())]

    # --- Process and Display Call Options Data ---
    print("\n--- CALL Options - OI Change ---")
    if call_data_list:
        try:
            calls_df = pd.DataFrame(call_data_list)
            if 'Strike Price' not in calls_df.columns:
                logging.error("Malformed call_data_list: 'Strike Price' column missing.")
                print(calls_df.to_string())
            else:
                calls_df.set_index('Strike Price', inplace=True)
                calls_df.rename(columns=oi_change_columns_map, inplace=True)
                
                # Format ATM strike in index
                if atm_strike in calls_df.index:
                    calls_df.rename(index={atm_strike: f"{float(atm_strike):.2f} (ATM)"}, inplace=True)
                
                # Select only the relevant OI change columns in the desired order
                display_df_calls = calls_df[ordered_display_columns]
                print(display_df_calls.to_string())
        except Exception as e:
            logging.error(f"Error processing call data for display: {e}")
            print("Could not display call data due to an error.")
    else:
        print("No data available for Call options.")

    # --- Process and Display Put Options Data ---
    print("\n--- PUT Options - OI Change ---")
    if put_data_list:
        try:
            puts_df = pd.DataFrame(put_data_list)
            if 'Strike Price' not in puts_df.columns:
                logging.error("Malformed put_data_list: 'Strike Price' column missing.")
                print(puts_df.to_string())
            else:
                puts_df.set_index('Strike Price', inplace=True)
                puts_df.rename(columns=oi_change_columns_map, inplace=True)

                # Format ATM strike in index
                if atm_strike in puts_df.index:
                    puts_df.rename(index={atm_strike: f"{float(atm_strike):.2f} (ATM)"}, inplace=True)

                # Select only the relevant OI change columns in the desired order
                display_df_puts = puts_df[ordered_display_columns]
                print(display_df_puts.to_string())
        except Exception as e:
            logging.error(f"Error processing put data for display: {e}")
            print("Could not display put data due to an error.")
    else:
        print("No data available for Put options.")
    
    print("-------------------------------------\n")

def extract_strike_from_symbol(symbol_str, underlying_prefix, expiry_details_str):
    """
    Extracts the strike price from an NFO option trading symbol string using regex.
    Tries multiple common patterns and includes a basic fallback.
    """
    # Attempt to match common NFO option symbol patterns
    # Pattern 1: PREFIX + YYMDD + STRIKE + CE/PE (e.g., NIFTY2462017000CE)
    pattern1_str = f"^{underlying_prefix}{expiry_details_str}(\d+)(CE|PE)$"
    match1 = re.match(pattern1_str, symbol_str, re.IGNORECASE)
    if match1:
        return float(match1.group(1))

    # Pattern 2: PREFIX + YYMMM + STRIKE + CE/PE (e.g., NIFTY24JUN17000CE) - expiry_details_str would be YYMMM
    # This pattern assumes expiry_details_str is like "24JUN"
    pattern2_str = f"^{underlying_prefix}{expiry_details_str}(\d+)(CE|PE)$"
    match2 = re.match(pattern2_str, symbol_str, re.IGNORECASE)
    if match2:
            return float(match2.group(1))

    # Pattern 3: PREFIX + DDMMMYY + STRIKE + CE/PE (e.g. BANKNIFTY20JUL2340500CE)
    # This pattern assumes expiry_details_str is like "20JUL23"
    pattern3_str = f"^{underlying_prefix}{expiry_details_str}(\d+)(CE|PE)$" # This is essentially same as pattern2 if expiry_details_str is flexible
    match3 = re.match(pattern3_str, symbol_str, re.IGNORECASE)
    if match3:
        return float(match3.group(1))
        
    logging.warning(f"Could not extract strike from symbol: {symbol_str} using known patterns with prefix '{underlying_prefix}' and expiry details '{expiry_details_str}'. Trying basic extraction.")
    
    # Basic fallback: remove prefix, expiry, and CE/PE and see if what's left is a number
    # This is less reliable and depends on the exact structure of expiry_details_str
    temp_str = symbol_str.upper().replace(underlying_prefix.upper(), "")
    temp_str = temp_str.replace(expiry_details_str.upper(), "")
    temp_str = temp_str.replace("CE", "").replace("PE", "")
    if temp_str.isdigit():
        return float(temp_str)
        
    logging.error(f"Critically failed to extract strike from {symbol_str}.")
    return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # --- User Configuration (ensure this is defined above in the global scope of the script) ---
    # Global vars like API_KEY, API_SECRET, ACCESS_TOKEN are defined at the top of the script.
    # Specific operational parameters:
    UNDERLYING_SYMBOL = "NIFTY 50" 
    EXCHANGE = "NSE" 
    OPTIONS_EXCHANGE = "NFO" 
    CURRENT_EXPIRY_DETAILS_STR = "24620" # Placeholder: YYMDD e.g. for 20th June 2024 - NEEDS VERIFICATION by user
    STRIKE_STEP = 50  
    COUNT_AROUND_ATM = 2 
    LOOP_DELAY_SECONDS = 60 # Time in seconds between updates
    # --- End User Configuration ---

    if API_KEY == "YOUR_API_KEY" or API_SECRET == "YOUR_API_SECRET":
        logging.critical("API_KEY or API_SECRET is not set. Please configure them in the script. Exiting.")
        exit()

    kite = KiteConnect(api_key=API_KEY)

    global ACCESS_TOKEN # To modify the global ACCESS_TOKEN if it's generated
    if not ACCESS_TOKEN or ACCESS_TOKEN == "YOUR_ACCESS_TOKEN":
        logging.info("Attempting to generate access token. Manual step required.")
        print(f"Login URL: {kite.login_url()}")
        request_tkn = input("Please login and enter the request_token: ")
        try:
            data = kite.generate_session(request_tkn, api_secret=API_SECRET)
            ACCESS_TOKEN = data["access_token"] # This updates the global ACCESS_TOKEN
            kite.set_access_token(ACCESS_TOKEN)
            logging.info(f"Successfully generated ACCESS_TOKEN: {ACCESS_TOKEN}")
            print(f"IMPORTANT: Store this ACCESS_TOKEN securely for future use (e.g. in the script's global ACCESS_TOKEN variable): {ACCESS_TOKEN}")
        except Exception as e:
            logging.critical(f"Access token generation failed: {e}. Exiting.")
            exit()
    else:
        try:
            kite.set_access_token(ACCESS_TOKEN)
            logging.info("Access token set successfully from configuration.")
            # Verify token by fetching profile (optional, but good check)
            profile = kite.profile()
            logging.info(f"Successfully connected to Kite. User: {profile.get('user_id')}")
        except Exception as e:
            logging.critical(f"Failed to set/validate access token: {e}. Please check or regenerate. Exiting.")
            exit()

    logging.info("Fetching NFO instruments data once...")
    fetch_nfo_instruments(kite)
    if not NFO_INSTRUMENTS_DATA:
        logging.critical("Failed to fetch NFO instruments. Exiting.")
        exit()
    
    # Derive prefix for option symbols, e.g., "NIFTY" from "NIFTY 50"
    underlying_prefix_for_symbols = UNDERLYING_SYMBOL.split(' ')[0].upper()
    logging.info(f"Using underlying prefix: {underlying_prefix_for_symbols} and expiry details: {CURRENT_EXPIRY_DETAILS_STR} for symbol generation.")

    try:
        while True:
            logging.info(f"--- Starting new update cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
            
            atm = get_atm_strike(kite, underlying_instrument_symbol=UNDERLYING_SYMBOL, exchange=EXCHANGE)
            if atm is None:
                logging.error("Could not determine ATM strike. Skipping this cycle.")
                time.sleep(30) # Shorter sleep on ATM failure before retrying
                continue

            logging.info(f"Current ATM for {UNDERLYING_SYMBOL} is: {atm}")
            
            call_strikes_symbols = get_relevant_strikes(atm, STRIKE_STEP, COUNT_AROUND_ATM, "CE", CURRENT_EXPIRY_DETAILS_STR, underlying_prefix=underlying_prefix_for_symbols)
            put_strikes_symbols = get_relevant_strikes(atm, STRIKE_STEP, COUNT_AROUND_ATM, "PE", CURRENT_EXPIRY_DETAILS_STR, underlying_prefix=underlying_prefix_for_symbols)
            
            logging.info(f"Target Call Symbols: {call_strikes_symbols}")
            logging.info(f"Target Put Symbols: {put_strikes_symbols}")

            call_data_for_table = []
            put_data_for_table = []

            active_symbols_to_process = call_strikes_symbols + put_strikes_symbols
            if not active_symbols_to_process:
                logging.warning("No strike symbols generated. Check ATM and relevant strike logic. Skipping cycle.")
                time.sleep(LOOP_DELAY_SECONDS)
                continue

            for symbol in active_symbols_to_process:
                option_type = "CE" if "CE" in symbol.upper() else "PE"
                strike_val = extract_strike_from_symbol(symbol, underlying_prefix_for_symbols, CURRENT_EXPIRY_DETAILS_STR)
                
                if strike_val is None:
                    logging.warning(f"Could not extract strike for {symbol}, skipping.")
                    continue
                
                logging.debug(f"Processing {option_type}: {symbol} (Strike: {strike_val})")
                oi_changes = calculate_oi_change(kite, symbol) # Default deltas: 10, 15, 30
                
                entry = {'Strike Price': strike_val, **oi_changes}
                
                if option_type == "CE":
                    call_data_for_table.append(entry)
                else:
                    put_data_for_table.append(entry)

            # Sort data by strike price before display
            call_data_for_table.sort(key=lambda x: x['Strike Price'])
            put_data_for_table.sort(key=lambda x: x['Strike Price'])
            
            display_tables(call_data_for_table, put_data_for_table, atm)
            
            logging.info(f"--- Update cycle complete. Waiting for {LOOP_DELAY_SECONDS} seconds. ---")
            time.sleep(LOOP_DELAY_SECONDS)

    except KeyboardInterrupt:
        logging.info("Script interrupted by user. Exiting...")
    except Exception as e:
        logging.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
    finally:
        logging.info("OI Tracker script finished.")
