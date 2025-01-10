from flask import Flask, render_template, Response
import yfinance as yf
import pandas as pd
from io import StringIO
import csv

app = Flask(_name_)

data = []  # This variable holds the processed ETF data
underperforming_etfs = [] 

# Function to add .NS extension
def add_extension(ticker_symbol):
    return ticker_symbol if ticker_symbol.endswith(".NS") else ticker_symbol + ".NS"

# Function to get current market price
def get_current_market_price(ticker_symbol):
    try:
        data = yf.Ticker(ticker_symbol)
        current_price = data.history(period="1d")["Close"].iloc[-1]
        return round(current_price, 2)
    except Exception as e:
        print(f"Error fetching current market price for {ticker_symbol}: {e}")
        return None

# Function to calculate 20-day moving average
def calculate_20_day_moving_average(ticker_symbol):
    try:
        today = pd.Timestamp.today()
        start_date = today - pd.Timedelta(days=60)
        data = yf.download(ticker_symbol, start=start_date, end=today)
        if data.empty or len(data) < 20:
            return None
        closing_prices = data["Close"]
        average_price = closing_prices.iloc[-20:].mean()
        return round(average_price, 3)
    except Exception as e:
        print(f"Error calculating 20-day moving average for {ticker_symbol}: {e}")
        return None

# Function to get volume
def get_volume(ticker_symbol):
    try:
        volume_data = yf.download(ticker_symbol, period="1d")['Volume']
        if volume_data.empty:
            return None
        return volume_data.iloc[-1]
    except Exception as e:
        print(f"Error fetching volume data for {ticker_symbol}: {e}")
        return None

@app.route('/')
def dashboard():
    input_file = r"D:\Download\MW-ETF-13-May-2024.csv"
    df = pd.read_csv(input_file, usecols=['SYMBOL'], names=['SYMBOL'], skiprows=1)

    #data = []
    #underperforming_etfs = []
    for index, row in df.iterrows():
        ticker_symbol = add_extension(row['SYMBOL'])
        volume = get_volume(ticker_symbol)

        if volume is not None and volume > 10000:
            current_price = get_current_market_price(ticker_symbol)
            if current_price is None:
                continue

            moving_average = calculate_20_day_moving_average(ticker_symbol)
            if moving_average is None:
                continue

            change = current_price - moving_average
            percent_change = (change / moving_average) * 100 if moving_average != 0 else 0

            data.append({
                'symbol': ticker_symbol,
                'dma': moving_average,
                'cmp': current_price,
                'change': change,
                'per_change': percent_change
            })

            if percent_change < 0:
                underperforming_etfs.append({
                    'symbol': ticker_symbol,
                    'cmp': current_price,
                    'per_change': percent_change
                })

    underperforming_etfs.sort(key=lambda x: x['per_change'])
    return render_template('dashboard.html', data=data, underperforming_etfs=underperforming_etfs[:10])

@app.route('/export', methods=['POST'])
def export_csv():
    csv_data = generate_csv(data, underperforming_etfs)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=my_data.csv"}
    )

def generate_csv(data_list, underperforming_etfs):
    output = StringIO()
    writer = csv.writer(output)

    # Write the header row for both tables with a gap of 2 columns
    header_row = ['Ticker Symbol', '20-Day Moving Average', 'Current Market Price', 'CMP-20DMA', '%Change']
    header_row.extend([''] * 2)  # Add 2 empty columns
    header_row.extend(['Ticker Symbol', 'Current Market Price', '% Change'] )
    writer.writerow(header_row)

    # Write data rows for both tables
    top_underperforming = sorted(underperforming_etfs, key=lambda x: x['per_change'])[:10]

    for item, underperforming_item in zip(data_list, top_underperforming + [{}] * (len(data_list) - len(top_underperforming))):
        row = [item['symbol'], item['dma'], item['cmp'], item['change'], item['per_change']]
        row.extend([''] * 2)  # Add 2 empty columns
        if underperforming_item:
            row.extend([underperforming_item['symbol'], underperforming_item['cmp'], underperforming_item['per_change']])
        else:
            row.extend([''] * 3)  # Add 3 empty columns for rows without underperforming data
        writer.writerow(row)

    return output.getvalue()
if _name_ == '_main_':
    app.run(debug=True)