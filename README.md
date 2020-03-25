# Corona-Tracker
Tracker for COVID-19 in the United States using data from the U.S CDC and John Hopkins University. This software powers a Twitter bot that you can follow [here](https://twitter.com/TrackerCorona)

# About
This software scrapes data from the [U.S Centers for Disease Control and Prevention](https://www.cdc.gov/coronavirus/2019-ncov/cases-in-us.html)
and [John Hopkins University CSSE](https://github.com/CSSEGISandData/COVID-19)
and (at present) creates simple visualizations of it. Usage of this software requires a Twitter developer account.
This is a very early release and new features are currently in development.

# Current Features
- Automatically checks JHU CSSE's COVID-19 repo for new reports and saves time series and daily total data as a CSV file
- Automatically generates and formats plots from data and saves plots as .png files
- Automatically formats and posts tweets with case information with support for generating threaded tweets

# Usage
This software requires a Twitter Developer Account. To install this software, follow these steps:

1. Clone this repo to a directory of your choice (Note that this program sets up its data in its install location)
2. Install the following packages and their dependencies: matplotlib, numpy, pandas, requests
3. Open a terminal window in your install location and run `python3 coronatracker.py`
4. Follow the terminal prompts to authorize this software to connect to your Twitter app

# Current Pitfalls
Since this software its dependent on 3rd party data that I have no control over, the functionality of this program is somewhat out of my control.
JHU has changed its spreadsheet data several times in a way that breaks this program, and it is possible it can happen again. The same goes for the CDC data.

# In-Development Features
- Comparisons with other countries
- Additional statistics and visualizations

# License and Acknowledgements
This software is licensed under the GNU GPL v3 and is provided without any warranty. This software is not developed by any government or international organization.
This software uses data from the United States Centers for Disease Control and Prevention as well as John Hopkins University CSSE and the author of this software is eternally grateful
to these institutions for making this data publically accessible.
