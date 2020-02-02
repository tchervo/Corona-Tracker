# Corona-Tracker
Tracker for 2019-nCoV in the United States using data from the U.S CDC and John Hopkins University

# About
This software scrapes data from the [U.S Centers for Disease Control and Prevention](https://www.cdc.gov/coronavirus/2019-ncov/cases-in-us.html)
and [John Hopkins University CSSE](https://docs.google.com/spreadsheets/d/1yZv9w9zRKwrGTaR-YzmAqMefw4wMlaXocejdxZaTs6w/htmlview?usp=sharing&sle=true)
and (at present) creates simple visualizations of it. Usage of this software requires a Google Cloud account with Google Sheets access enabled.
This is a very early release and new features are currently in development.

# Usage
This software requires a Google Cloud account with Google Sheets enabled. To install this software, follow these steps:

1. Clone this repo to a directory of your choice (Note that this program sets up its data in its install location)
2. Install the following packages and their dependencies: matplotlib, numpy, pandas, requests, bs4, oauth2client, gspread
3. Either create or sign in to your Google Cloud account, enable the Google Sheets API (this may take a bit), download your credentials file, name it 'credentials.json', and drop it in your install location
4. Open a terminal window in your install location and run `python coronatracker.py`

# Current Pitfalls
Since this software its dependent on 3rd party data that I have no control over, the functionality of this program is somewhat out of my control.
JHU has changed its spreadsheet data several times in a way that breaks this program, and it is possible it can happen again. The same goes for the CDC data.

# In-Development Features
- Twitter support
- Comparisons with other countries
- Additional statistics and visualizations

# License and Acknowledgements
This software is licensed under the GNU GPL v3 and is provided without any warranty. This software is not developed by any government or international organization.
This software uses data from the United States Centers for Disease Control and Prevention as well as John Hopkins University CSSE and the author of this software is eternally grateful
to these institutions for making this data publically accessible.
