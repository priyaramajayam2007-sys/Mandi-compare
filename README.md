\# Mandi Price Compare



A web app that helps farmers compare crop prices across mandis (wholesale markets) in Tamil Nadu, so they can see where a crop is selling for the most.



\## Features

\- Pick a crop, variety, and grade to compare like with like

\- Shows the latest modal price reported by each market

\- Highlights the market with the highest price

\- Table and bar chart view

\- Data loaded into a local SQLite database, so the app stays fast



\## Tech stack

Python, Flask, SQLite, pandas, HTML, Chart.js



\## How to run

1\. Install packages: `pip install -r requirements.txt`

2\. Load the data: `python load\_data.py "Madurai banana.csv"`

3\. Start the app: `python server.py`

4\. Open http://127.0.0.1:5000



\## Data source

Daily mandi prices from Agmarknet (Government of India), downloaded from data.gov.in. Prices are usually reported per quintal; please confirm the unit on the data.gov.in dataset page.



\## Roadmap

\- \[ ] Add more districts and crops

\- \[ ] Fetch data automatically every day through the API

\- \[ ] Price trend chart

\- \[ ] "Best place to sell" after transport cost

\- \[ ] Deploy with a live link

