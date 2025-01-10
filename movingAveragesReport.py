from collections import namedtuple
import yfinance as yf
from prettytable import PrettyTable
from moving_averages_repository import save_moving_averages_results, fetch_yesterday_moving_averages
from telegram_logging_handler import app_logger
from sql_connection import Symbol
from typing import List

def create_moving_averages_tables(symbols: List[Symbol], conn) -> tuple[PrettyTable, PrettyTable]:
    ma_values = []
    ema_values = []
    MAData = namedtuple('MAData', ['symbol', 'current_price', 'ma50', 'ma200', 'ma50_status', 'ma200_status'])
    EMAData = namedtuple('EMAData', ['symbol', 'current_price', 'ema50', 'ema200', 'ema50_status', 'ema200_status'])
    yesterdayValues = fetch_yesterday_moving_averages(conn)

    for symbol in symbols:
        try:
            app_logger.info('Processing symbol: %s', symbol.symbol_name)
            ticker = yf.Ticker(symbol.yf_name)
            df = ticker.history(interval="1d", period="max")
            app_logger.info('Retrieved %d data points for %s', len(df), symbol.symbol_name)
            
            # Calculate all indicators at once
            df['MA50'] = df['Close'].rolling(window=50).mean()
            df['MA200'] = df['Close'].rolling(window=200).mean()
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
            
            today_price = df['Close'].iloc[-1]
            today_MA50 = df['MA50'].iloc[-1]
            today_MA200 = df['MA200'].iloc[-1]
            today_EMA50 = df['EMA50'].iloc[-1]
            today_EMA200 = df['EMA200'].iloc[-1]
            
            # Initialize status indicators
            ma50_status = "🟢" if today_price > today_MA50 else "🔴"
            ma200_status = "🟢" if today_price > today_MA200 else "🔴"
            ema50_status = "🟢" if today_price > today_EMA50 else "🔴"
            ema200_status = "🟢" if today_price > today_EMA200 else "🔴"
            
            # Check for crossovers if we have yesterday's data
            if not yesterdayValues.empty:
                yesterday_data = yesterdayValues[yesterdayValues['SymbolName'] == symbol.symbol_name]
                if not yesterday_data.empty:
                    yesterday_price = yesterday_data['CurrentPrice'].iloc[0]
                    yesterday_ma50 = yesterday_data['MA50'].iloc[0]
                    yesterday_ma200 = yesterday_data['MA200'].iloc[0]
                    yesterday_ema50 = yesterday_data['EMA50'].iloc[0]
                    yesterday_ema200 = yesterday_data['EMA200'].iloc[0]
                    
                    # MA Crossovers
                    if yesterday_price < yesterday_ma50 and today_price > today_MA50:
                        ma50_status = "🚨🟢"
                        app_logger.info(f"{symbol.symbol_name} crossed above MA50")
                    elif yesterday_price > yesterday_ma50 and today_price < today_MA50:
                        ma50_status = "🚨🔴"
                        app_logger.info(f"{symbol.symbol_name} crossed below MA50")
                    
                    if yesterday_price < yesterday_ma200 and today_price > today_MA200:
                        ma200_status = "🚨🟢"
                        app_logger.info(f"{symbol.symbol_name} crossed above MA200")
                    elif yesterday_price > yesterday_ma200 and today_price < today_MA200:
                        ma200_status = "🚨🔴"
                        app_logger.info(f"{symbol.symbol_name} crossed below MA200")
                    
                    # EMA Crossovers
                    if yesterday_price < yesterday_ema50 and today_price > today_EMA50:
                        ema50_status = "🚨🟢"
                        app_logger.info(f"{symbol.symbol_name} crossed above EMA50")
                    elif yesterday_price > yesterday_ema50 and today_price < today_EMA50:
                        ema50_status = "🚨🔴"
                        app_logger.info(f"{symbol.symbol_name} crossed below EMA50")
                    
                    if yesterday_price < yesterday_ema200 and today_price > today_EMA200:
                        ema200_status = "🚨🟢"
                        app_logger.info(f"{symbol.symbol_name} crossed above EMA200")
                    elif yesterday_price > yesterday_ema200 and today_price < today_EMA200:
                        ema200_status = "🚨🔴"
                        app_logger.info(f"{symbol.symbol_name} crossed below EMA200")
            
            # Store the results
            ma_values.append(MAData(
                symbol=symbol.symbol_name,
                current_price=today_price,
                ma50=today_MA50,
                ma200=today_MA200,
                ma50_status=ma50_status,
                ma200_status=ma200_status
            ))
            
            ema_values.append(EMAData(
                symbol=symbol.symbol_name,
                current_price=today_price,
                ema50=today_EMA50,
                ema200=today_EMA200,
                ema50_status=ema50_status,
                ema200_status=ema200_status
            ))
            
            # Save to database
            if conn:
                try:
                    save_moving_averages_results(
                        conn=conn,
                        symbol_id=symbol.symbol_id,
                        current_price=today_price,
                        ma50=today_MA50,
                        ma200=today_MA200,
                        ema50=today_EMA50,
                        ema200=today_EMA200
                    )
                except Exception as e:
                    app_logger.error(f"Failed to save moving averages results for {symbol.symbol_name}: {str(e)}")
                    
        except Exception as e:
            app_logger.error('Error processing symbol %s: %s', symbol.symbol_name, str(e))

    # Create MA table
    ma_table = PrettyTable()
    ma_table.field_names = ["Symbol", "Current", "MA50", "MA200"]

    # Create EMA table
    ema_table = PrettyTable()
    ema_table.field_names = ["Symbol", "Current", "EMA50", "EMA200"]

        # Format numbers just before displaying in table
    def format_price(price):
        # Convert to string with standard notation (no scientific)
        str_price = f"{price:.10f}"
        # Remove trailing zeros after decimal
        str_price = str_price.rstrip('0').rstrip('.')
        # Count total digits excluding decimal point
        total_digits = sum(c.isdigit() for c in str_price)
        
        if total_digits > 6:
            # If more than 6 digits, round to appropriate decimal places
            decimal_idx = str_price.find('.')
            if decimal_idx == -1:
                return str(round(price))[:6]  # No decimal point
            else:
                before_decimal = decimal_idx
                allowed_after_decimal = 6 - before_decimal
                return f"{price:.{max(0, allowed_after_decimal)}f}"
        return str_price

    # Fill both tables
    for ma_row, ema_row in zip(ma_values, ema_values):
        ma_table.add_row([
            ma_row.symbol,
            format_price(ma_row.current_price),
            f"{format_price(ma_row.ma50)} {ma_row.ma50_status}",
            f"{format_price(ma_row.ma200)} {ma_row.ma200_status}",
        ])
        
        ema_table.add_row([
            ema_row.symbol,
            format_price(ema_row.current_price),
            f"{format_price(ema_row.ema50)} {ema_row.ema50_status}",
            f"{format_price(ema_row.ema200)} {ema_row.ema200_status}",
        ])

    return ma_table, ema_table