import os
import time
import logging
import json
import random
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import tweepy as tw

jhu_path = os.getcwd() + '/jhu_data/'
cdc_path = os.getcwd() + '/cdc_data/'
plot_path = os.getcwd() + '/plots/'
twitter_file = os.getcwd() + '/twitter_creds.json'

now = datetime.now()
now_file_ext = now.strftime('%m_%d_%H_%M_%S.csv')

log_path = os.getcwd() + '/logs/coronatracker_log.log'
log_format = '%(levelname)s | %(asctime)s | %(message)s'

should_tweet = False

if os.path.exists(twitter_file):
    with open(twitter_file, 'r') as file:
        twitter_creds = json.load(file)

    consumer_key = twitter_creds['consumer_key']
    consumer_secret = twitter_creds['consumer_secret']
    access_token = twitter_creds['access_token']
    access_secret = twitter_creds['access_secret']
    auth = tw.OAuthHandler(consumer_key, consumer_secret)

    auth.set_access_token(access_token, access_secret)
else:
    consumer_key = input('Input your Twitter consumer key: ')
    consumer_secret = input('Input your Twitter consumer secret: ')
    auth = tw.OAuthHandler(consumer_key, consumer_secret)
    redirect_url = auth.get_authorization_url()

    print('Please click this link to authorize CoronaTracker: {}'.format(redirect_url))
    verifier = input('Enter the verification code you received from Twitter: ')
    auth.get_access_token(verifier)

    data = {'consumer_key': consumer_key, 'consumer_secret': consumer_secret, 'access_token': auth.access_token,
            'access_secret': auth.access_token_secret}

    with open(twitter_file, 'w') as file:
        json.dump(data, file)

api = tw.API(auth, wait_on_rate_limit=True)

state_map = {'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'CA': 'California', 'CO': 'Colorado',
             'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii',
             'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky',
             'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan',
             'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska',
             'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
             'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon',
             'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
             'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
             'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'}

if os.path.exists(os.getcwd() + '/logs/') is not True:
    try:
        os.mkdir(os.getcwd() + '/logs/')
    except OSError as error:
        print(f'Could not create log directory because {error.strerror}!')

logging.basicConfig(filename=log_path, format=log_format, filemode='w', level=logging.INFO)

logger = logging.getLogger()


def get_jhu_data() -> pd.DataFrame:
    """
    Connects to Google Sheets API and gets data for the United States from JHU's tracker
    :return A pandas dataframe with columns state, city, cases, deaths, recoveries
    """
    logger.info('Attempting to connect to JHU sheet')

    # Time series: 1UF2pSkFTURko2OvfHWWlFpDFAr1UxCBA4JLwlSP6KFo
    jhu_sheet_id = '1wQVypefm946ch4XDp37uZ-wartW4V7ILdg-qYiDXUHM'
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(jhu_sheet_id)
    newest_sheet = sheet.worksheets()[0]

    us_cities = []
    us_states = []
    us_cases = []
    us_deaths = []
    us_recoveries = []

    for row in newest_sheet.get_all_values():
        region = row[0]
        country = row[1]
        cases = row[3]
        deaths = row[4]
        recoveries = row[5]

        if country == 'US':
            # Regions don't get entered unless they have cases, so we know we can always convert this
            cases = int(cases)

            # Deaths and recoveries are usually entered as a blank value if there are no values
            # so we have to be careful
            try:
                deaths = int(deaths)
                recoveries = int(recoveries)
            except ValueError:
                deaths = 0
                recoveries = 0

            city, state = region.split(',')

            us_states.append(state_map[state.replace(' ', '')])
            us_cities.append(city)
            us_cases.append(cases)
            us_deaths.append(deaths)
            us_recoveries.append(recoveries)

    data = {'state': us_states, 'city': us_cities, 'cases': us_cases, 'deaths': us_deaths, 'recoveries': us_recoveries}
    frame = pd.DataFrame(data)

    if frame.empty is not True:
        logger.info('Successfully downloaded JHU data! If new will save as jhu_{}'.format(now_file_ext))

    newest_data = get_most_recent_data('jhu')

    if is_new_data(frame, newest_data, 'jhu'):
        print('Found new data! Saving...')
        logger.info('Found new data! Now saving...')
        frame.to_csv(jhu_path + 'jhu_' + now_file_ext)
        global should_tweet
        should_tweet = True
    else:
        logger.warning('Downloaded data is not new! Will not save')

    return frame


def get_time_series():
    """
    Reads data from the JHU time series sheet
    :return: A dataframe of the time series data for the U.S
    """
    time_sheet_id = '1UF2pSkFTURko2OvfHWWlFpDFAr1UxCBA4JLwlSP6KFo'
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(time_sheet_id)
    cases_sheet = sheet.worksheets()[0]

    dates = []
    states = []
    cases = []

    for row in cases_sheet.get_all_values():
        country = row[1]

        # Checks to see if we are in the column names row
        if row[0] == 'Province/State':
            date_times = row[5:len(row) - 1]
        if country == 'US':
            pass


def get_data_for(name: str, var: str, data: pd.DataFrame, region='state') -> pd.Series:
    """
    Allows for selection of data by variable at the state or city level
    :param data: The dataframe to select from
    :param var: The variable to select. Valid inputs are cases, deaths, and recoveries
    :param name: The name of the location (i.e Berkeley or California)
    :param region: Whether to select based on state level data or city level data. Default is state. Valid inputs are
    city and state
    :return: A Series containing the requested data
    """

    if region == 'state':
        target_frame = data[data.state.str.contains(name)]

        return target_frame[var]
    elif region == 'city':
        target_frame = data[data.city.str.contains(name)]

        return target_frame[var]
    else:
        logger.warning('Received invalid region {}'.format(region))
        raise ValueError('Unknown region {}! Region must be either state or city!'.format(region))


def make_state_frame(data: pd.DataFrame) -> pd.DataFrame:
    """
    Creates a dataframe containing data at the state level
    :param data: The dataframe to ready values from
    :return: A data frame containing the same data from the JHU frame but organized at the state level
    """
    state_deaths = []
    state_cases = []
    state_recoveries = []
    states = []

    for state in data['state']:
        deaths = get_data_for(state, 'deaths', data)
        cases = get_data_for(state, 'cases', data)
        recoveries = get_data_for(state, 'recoveries', data)

        if state not in states:
            states.append(state)
            state_deaths.append(deaths.sum())
            state_cases.append(cases.sum())
            state_recoveries.append(recoveries.sum())

    ret_data = {'state': states, 'cases': state_cases, 'deaths': state_deaths, 'recoveries': state_recoveries}

    return pd.DataFrame(ret_data)


def is_new_data(recent_data: pd.DataFrame, prev_data: pd.DataFrame, source: str) -> bool:
    """
    Checks to see if the data that was recently fetched is the same as existing data
    :param source: The source of the data. Determines what columns to select. Valid inputs are cdc or jhu
    :param recent_data: The most recently fetched data
    :param prev_data: The dataframe to compare to
    :return: True or false depending on whether or not the recent_data dataframe is newer than the previous one
    """
    columns = []
    is_new = False
    if source == 'jhu':
        columns = ['state', 'cases', 'deaths', 'recoveries']
    if source == 'cdc':
        columns = ['measure', 'counts']

    if prev_data.empty:
        return True
    else:
        # Since the CDC data is formatted consistently, particularly smart data checking is not needed
        if source == 'cdc':
            for column in columns:
                for entry1, entry2 in zip(recent_data[column], prev_data[column]):
                    if entry1 != entry2:
                        is_new = True
                        break
        # JHU data requires a bit more thinking
        if source == 'jhu':
            states_new = []
            states_old = []
            city_new_data_map = {}
            city_old_data_map = {}

            # Suspected new data is suffixed with 'new' and suspected old data is suffixed with 'old'
            for tuple_new, tuple_old in zip(recent_data.iterrows(), prev_data.iterrows()):
                # Iterates through each value in the row
                row_data_new = [entry for entry in tuple_new[1]]
                state_new = row_data_new[0]
                city_new = row_data_new[1]
                case_data_new = row_data_new[2:5]

                states_new.append(state_new)
                city_new_data_map[city_new] = case_data_new

                row_data_old = [entry for entry in tuple_old[1]]
                state_old = row_data_old[1]
                city_old = row_data_old[2]
                case_data_old = row_data_old[3:6]

                states_old.append(state_old)
                city_old_data_map[city_old] = case_data_old

            if states_new.sort() != states_old.sort():
                is_new = True
            for city in city_new_data_map.keys():
                if city not in city_old_data_map.keys():
                    is_new = True
                    break
                else:
                    if city_new_data_map[city] != city_old_data_map[city]:
                        is_new = True
                        break

        return is_new


def get_cdc_data() -> pd.DataFrame:
    """
    Scans the web page at the URL listed below for a table containing test result status for the United States
    :return: A dataframe with the columns measure and counts
    """

    cdc_url = 'https://www.cdc.gov/coronavirus/2019-ncov/cases-in-us.html'
    cdc_page = requests.get(cdc_url)
    cdc_soup = BeautifulSoup(cdc_page.content, features='html.parser')

    measures = []
    values = []

    table = cdc_soup.find('table')
    rows = table.find_all('tr')

    for entry in rows:
        measure_name = str(entry.find('th').get_text()).replace('§', '').replace(':', '')
        measure_val = int(entry.find('td').get_text())

        if measure_name != 'Total':
            measures.append(measure_name)
            values.append(measure_val)

    data = {'measure': measures, 'counts': values}
    frame = pd.DataFrame(data)

    if frame.empty is not True:
        logger.info('Successfully downloaded CDC data! If new will save as cdc_{}'.format(now_file_ext))

    newest_data = get_most_recent_data('cdc')

    if is_new_data(frame, newest_data, 'cdc'):
        print('Found new data! Saving...')
        logger.info('Found new data! Now saving...')
        frame.to_csv(cdc_path + 'cdc_' + now_file_ext)
        global should_tweet
        should_tweet = True
    else:
        logger.warning('Downloaded data is not new! Will not save')

    return frame


def load_all_data(data_type: str) -> []:
    """
    Loads all of the data from a directory of a given type. (Ex. All the data from the CDC directory
    :param data_type: What type of data to download. Valid types are jhu or cdc
    :return: A list of all files in the directory
    """
    data = []

    if data_type.lower() == 'cdc':
        for file in os.listdir(cdc_path):
            if file != '.DS_Store':
                data.append(file)
    if data_type.lower() == 'jhu':
        for file in os.listdir(jhu_path):
            if file != '.DS_Store':
                data.append(file)

    return data


def get_most_recent_data(data_source: str) -> pd.DataFrame:
    """
    Returns a dataframe of the most recently downloaded data of a certain type
    :param data_source: The source of the data to load. Valid sources are jhu or cdc
    :return: A dataframe of the most recently downloaded data of a certain type
    """

    candidate_file = ''
    # We look at the difference between right now and when the file was created, and select the lowest difference
    curr_lowest_diff = None

    if load_all_data(data_source) != []:
        for file in load_all_data(data_source):
            file_time = file[5:18]
            time_components = file_time.split('_')
            file_datetime = datetime(2020, int(time_components[0]), int(time_components[1]),
                                     hour=int(time_components[2]),
                                     minute=int(time_components[3]), second=int(time_components[4]))
            time_diff = now - file_datetime

            if curr_lowest_diff is not None:
                if time_diff < curr_lowest_diff:
                    curr_lowest_diff = time_diff
                    candidate_file = file
            else:
                curr_lowest_diff = time_diff
                candidate_file = file

        if data_source == 'jhu':
            candidate_file = jhu_path + candidate_file
        if data_source == 'cdc':
            candidate_file = cdc_path + candidate_file

        return pd.read_csv(candidate_file)
    else:
        return pd.DataFrame()


def make_tweet():
    """Creates a tweet to post to Twitter"""

    hashtags = ['#nCoV', '#Coronavirus', '#USCoronavirus', '#2019nCoV']
    chosen_tags = random.sample(hashtags, k=2)
    text = f'2019-nCoV Update: This tracker detected new information {chosen_tags[0]} {chosen_tags[1]}'
    media_ids = []
    files = [plot_path + 'state_sum.png', plot_path + 'city_sum.png']

    for file in files:
        response = api.media_upload(file)
        media_ids.append(response.media_id)

    print('Sending tweet!')
    logger.info('Found new data! Sending tweet!')

    api.update_status(status=text, media_ids=media_ids)


def main(first_run=True):
    if first_run:
        if os.path.exists(cdc_path) is not True:
            try:
                os.mkdir(cdc_path)
            except OSError as error:
                logger.critical(f'Could not create CDC data directory because {error.strerror}!')
        if os.path.exists(jhu_path) is not True:
            try:
                os.mkdir(jhu_path)
            except OSError as error:
                logger.critical(f'Could not create JHU data directory because {error.strerror}!')
        if os.path.exists(plot_path) is not True:
            try:
                os.mkdir(plot_path)
            except OSError as error:
                logger.critical(f'Could not create plots directory because {error.strerror}!')

    logger.info('Starting tracker loop')

    spacer = ' ' * 10

    if first_run:
        print('=' * 50,
              '\n',
              spacer + '2019-nCoV Tracker (U.S)\n',
              '=' * 50)
        print('To break this program out of its loop, press Ctrl+C')

    us_frame = get_jhu_data()
    cdc_frame = get_cdc_data()

    print('Displaying plots!')
    # General Plot Setup. Plots are "shown" then immediately closed to refresh the figure
    fig, (jhu_ax, cdc_ax) = plt.subplots(1, 2, figsize=(20, 10))
    fig.suptitle('2019-nCoV Details for the United States')
    # Plot setup for CDC figure
    cdc_ax.bar(x=cdc_frame['measure'], height=cdc_frame['counts'])
    cdc_ax.set_xlabel('Test Result')
    cdc_ax.set_ylabel('Count')
    cdc_ax.set_title('Positive, Negative, and Pending 2019-nCoV Cases in the United States')
    # Plot setup for JHU figure
    state_frame = make_state_frame(us_frame)
    # Interval is [Start, Stop) so we need to go one more
    jhu_ax.set_yticks(np.arange(start=0, stop=state_frame['cases'].max() + 1))
    jhu_ax.bar(x=state_frame['state'], height=state_frame['cases'])
    jhu_ax.set_xlabel('State')
    jhu_ax.set_ylabel('Confirmed Cases')
    jhu_ax.set_title('Confirmed 2019-nCoV Cases in the United States by State')
    plt.savefig(plot_path + 'state_sum.png')
    plt.show(block=False)
    plt.close()
    # Plot setup for city data
    plt.title('2019-nCoV Cases by city')
    plt.gcf().set_size_inches(10, 10)
    plt.xticks(rotation=45)
    plt.yticks(np.arange(start=0, stop=us_frame['cases'].max() + 1))
    plt.bar(x=us_frame['city'], height=us_frame['cases'])
    plt.xlabel('City')
    plt.ylabel('Confirmed Cases')
    plt.savefig(plot_path + 'city_sum.png')
    plt.show(block=False)
    plt.close()

    if should_tweet:
        # make_tweet()
        pass

    try:
        while True:
            print('Sleeping now for 30 minutes! Will check for new data afterwards...')
            time.sleep(60 * 30)
            main(first_run=False)
            break
    except KeyboardInterrupt:
        print('Exiting...')


if __name__ == '__main__':
    main()
