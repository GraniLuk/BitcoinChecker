from sharedCode.binance import fetch_binance_price
from prettytable import PrettyTable
from stepn.stepn_repository import save_stepn_results, fetch_stepn_results_last_14_days
import pandas as pd
from sharedCode.coingecko import fetch_coingecko_price
from source_repository import Symbol
from infra.telegram_logging_handler import app_logger
from stepn.stepn_ratio_fetch import fetch_gstgmt_ratio_range

def fetch_stepn_report(conn) -> PrettyTable:
    symbols = [
    Symbol(symbol_id=1, symbol_name='GMT', full_name='STEPN Token', source_id=3),
    Symbol(symbol_id=2, symbol_name='GST', full_name='green-satoshi-token-bsc', source_id=3)
    ]
    results = []
    
    try:
        ticker = fetch_binance_price(symbols[0])
        gmt_price = (ticker.symbol, ticker.last)
        results.append(gmt_price)
    except Exception as e:
        app_logger.error(f"Unexpected error for GMT: {str(e)}")
        raise
    
    try: 
        ticker = fetch_coingecko_price(symbols[1])
        gst_price = (ticker.symbol, ticker.last)
        results.append(gst_price)
    except Exception as e:
        app_logger.error(f"Unexpected error for GST: {str(e)}")
        raise
             
    # Calculate ratio
    gmt_gst_ratio = results[0][1]/results[1][1]
    
    # Fetch and calculate 24h range
    gst_ratio_result = fetch_gstgmt_ratio_range()
    min_24h, max_24h, range_percent = None, None, None
    if gst_ratio_result:
        min_24h, max_24h, range_percent = fetch_gstgmt_ratio_range()

    if conn is not None:
        last_14_days_results = fetch_stepn_results_last_14_days(conn)
        ratios = [record[2] for record in last_14_days_results]  # Extracting ratios separately
        ratios.append(gmt_gst_ratio)
        ema14_results = calculate_ema14(ratios)
        results.append(('EMA14', ema14_results[-1]))
    
        # Save results to database
        try:
            save_stepn_results(
                conn=conn, 
                gmt_price=results[0][1], 
                gst_price=results[1][1], 
                ratio=gmt_gst_ratio, 
                ema=ema14_results[-1],
                min_24h=min_24h,
                max_24h=max_24h,
                range_24h=range_percent
            )
        except Exception as e:
            app_logger.error(f"Error saving STEPN results to database: {str(e)}")
    
    # Create table for display
    stepn_table = PrettyTable()
    stepn_table.field_names = ["Symbol", "Current Price"]

    # Store rows with range calculation
    results.append(('GMT/GST', gmt_gst_ratio))


    # Add 24h statistics
    if min_24h and max_24h and range_percent:
        results.append(('24h Min', round(min_24h, 4)))
        results.append(('24h Max', round(max_24h, 4)))
        range_percent_formatted = f"{range_percent:.2f}%"
        results.append(('24h Range %', range_percent_formatted))

    for row in results:
        stepn_table.add_row(row)
    return stepn_table

def calculate_ema14(ratios):
        """
        Calculates the 14-day Exponential Moving Average (EMA) for the ratio column using pandas.

        Args:
            ratios (list of float): List of ratio values.

        Returns:
            list: EMA14 values for the provided ratios.
        """
        if not ratios:
            return []

        df = pd.DataFrame(ratios, columns=["Ratio"])
        df["EMA14"] = df["Ratio"].ewm(span=14, adjust=False).mean()

        return df["EMA14"].tolist()

if __name__ == "__main__":
    report = fetch_stepn_report(None)
    print(report)