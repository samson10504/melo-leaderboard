from io import StringIO

import pandas as pd
from flask import Flask, render_template_string, request

app = Flask(__name__)

# Your existing functions here (for brevity, not repeated)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            return 'No selected file'
        if file:
            # Convert string data to StringIO, then to DataFrame
            string_data = StringIO(file.read().decode('utf-8'))
            df = pd.read_csv(string_data)

            # Collect year and month from user input
            year = int(request.form['year'])
            month = int(request.form['month'])

            # Process the uploaded file
            processed_data = process_data(df, year, month)
            return render_template_string("""
            <!doctype html>
            <title>Results</title>
            <h2>Processed Data:</h2>
            <p>{{data|safe }}</p>
            <a href="/">Upload another file</a>
            """, data=processed_data)
    return '''
    <!doctype html>
    <title>Upload CSV File</title>
    <h2>Upload new CSV</h2>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type="number" name="year" placeholder="Year" required>
      <input type="number" name="month" placeholder="Month" required>
      <input type=submit value=Upload>
    </form>
    '''

def load_and_prepare_data(df, year, month):
    df['MemberEvent.Date'] = pd.to_datetime(df['MemberEvent.Date'])
    
    # Calculate cutoff date for filtering
    cutoff_date = pd.Timestamp(year=year, month=month, day=1, tz='UTC') + pd.DateOffset(months=1)
    filtered_df = df[df['MemberEvent.Date'] < cutoff_date]
    return filtered_df

def get_first_5_token_holders(df):
    latest_entries = df.sort_values(by='MemberEvent.Date', ascending=False).drop_duplicates(subset='MemberEvent.Member.Person.DisplayName')
    top_5_holders = latest_entries.sort_values(by='MemberEvent.MetaData.points-after-change', ascending=False).head(5)
    return top_5_holders[['MemberEvent.Member.Person.DisplayName', 'MemberEvent.MetaData.points-after-change']]

def calculate_positive_earnings(df, year, month):
    positive_earnings_df = df.copy()
    positive_earnings_df['Net Positive Earnings'] = positive_earnings_df['MemberEvent.MetaData.points-after-change'] - positive_earnings_df['MemberEvent.MetaData.points-before-change']
    positive_earnings_df = positive_earnings_df[(positive_earnings_df['Net Positive Earnings'] > 0) & 
                                                 (positive_earnings_df['MemberEvent.Date'].dt.year == year) & 
                                                 (positive_earnings_df['MemberEvent.Date'].dt.month == month)]
    total_positive_earnings = positive_earnings_df.groupby('MemberEvent.Member.Person.DisplayName')['Net Positive Earnings'].sum().reset_index()
    top_5_positive_earnings = total_positive_earnings.sort_values(by='Net Positive Earnings', ascending=False).head(5)
    return top_5_positive_earnings

def calculate_total_tokens(df, year, month):
    df['Net Earnings'] = df['MemberEvent.MetaData.points-after-change'] - df['MemberEvent.MetaData.points-before-change']
    month_specific_df = df[(df['MemberEvent.Date'].dt.year == year) & (df['MemberEvent.Date'].dt.month == month)]
    tokens_issued_month = month_specific_df[month_specific_df['Net Earnings'] > 0]['Net Earnings'].sum()
    tokens_spent_month = month_specific_df[month_specific_df['Net Earnings'] < 0]['Net Earnings'].sum()
    return tokens_issued_month, tokens_spent_month, tokens_issued_month + tokens_spent_month

# Main processing function
def process_data(df, year, month):
    df = load_and_prepare_data(df, year, month)
    results_html = "<h3>First 5 Token Holders (Latest Entry Per Member):</h3>"
    results_html += get_first_5_token_holders(df).to_html(index=False)
    
    results_html += "<h3>Top 5 Total Positive Token Earners of the Specified Month:</h3>"
    results_html += calculate_positive_earnings(df, year, month).to_html(index=False)
    
    tokens_issued, tokens_spent, net_tokens = calculate_total_tokens(df, year, month)
    summary_df = pd.DataFrame({
        "Category": ["Tokens Issued", "Tokens Spent", "Net Tokens"],
        "Amount": [tokens_issued, tokens_spent, net_tokens]
    })
    results_html += "<h3>Total Tokens Issued, Spent, and Net of the Specified Month:</h3>"
    results_html += summary_df.to_html(index=False)
    
    return results_html



if __name__ == '__main__':
    app.run(debug=True)
