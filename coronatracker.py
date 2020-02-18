import os
import time
import logging
import json
import random
import urllib
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
import tweepy as tw
from geohelper import *

jhu_path = os.getcwd() + '/jhu_data/'
cdc_path = os.getcwd() + '/cdc_data/'
plot_path = os.getcwd() + '/plots/'
twitter_file = os.getcwd() + '/twitter_creds.json'

now = datetime.now()
now_file_ext = now.strftime('%m_%d_%H_%M_%S.csv')

log_path = os.getcwd() + '/logs/coronatracker_log.log'
log_format = '%(levelname)s | %(asctime)s | %(message)s'

should_tweet = False
should_save_jhu = False

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
    Reads the name of update files on JHU's Github, selects the most recent one, and then downloads that file as a
    temp file to create a DataFrame. This DataFrame undergoes some reorganization to select for U.S data
    :return A pandas dataframe with columns state, city, cases, deaths, recoveries
    """
    logger.info('Attempting to connect to JHU sheet')

    jhu_github_url = 'https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data/csse_covid_19_daily_reports'
    github_req = requests.get(jhu_github_url)
    git_soup = BeautifulSoup(github_req.content, features='html.parser')

    candidate_link = ''
    curr_low_diff = None

    for link in git_soup.find_all('a'):
        if link.get('title') is not None and str(link.get('title')).endswith('.csv') and 'commit' not in \
                str(link.get('href')):
            file_name = link.get('title')
            file_date = file_name.replace('.csv', '').split('-')
            # file_time = file_date[2].split('_')[1]
            file_datetime = datetime(2020, int(file_date[0]), int(file_date[1]))

            if curr_low_diff is None:
                candidate_link = link.get('href')
                curr_low_diff = now - file_datetime
            else:
                diff = now - file_datetime

                if diff < curr_low_diff:
                    curr_low_diff = diff
                    candidate_link = link.get('href')

    file_link = str('https://raw.githubusercontent.com' + candidate_link).replace('blob/', '')
    newest_csv_req = urllib.request.Request(file_link)
    csv_file = urllib.request.urlopen(newest_csv_req)
    csv_data = csv_file.read()

    with open(jhu_path + 'jhu_temp.csv', 'wb') as file:
        file.write(csv_data)

    temp_frame = pd.read_csv(jhu_path + 'jhu_temp.csv')
    us_frame = temp_frame[['Province/State', 'Country/Region', 'Confirmed', 'Deaths', 'Recovered']]
    is_US = us_frame['Country/Region'] == 'US'
    us_frame = us_frame[is_US]
    us_frame.rename(columns={'Province/State': 'case_loc'}, inplace=True)
    cities = []
    states = []

    for entry in us_frame.case_loc:
        loc_list = entry.split(',')
        cities.append(loc_list[0])
        state_ab = loc_list[1].replace(' ', '')
        state_name = state_map.get(state_ab)
        states.append(state_name)

    temp_state_city_frame = pd.DataFrame({'state': states, 'city': cities}).reset_index(drop=True)
    us_frame = us_frame[['Confirmed', 'Deaths', 'Recovered']].reset_index(drop=True)
    frame = temp_state_city_frame.join(us_frame)
    rename_map = {'Confirmed': 'cases', 'Deaths': 'deaths', 'Recovered': 'recoveries'}

    frame.rename(columns=rename_map, inplace=True)

    os.remove(jhu_path + 'jhu_temp.csv')

    if frame.empty is not True:
        logger.info('Successfully downloaded JHU data! If new will save as jhu_{}'.format(now_file_ext))

    newest_data = get_most_recent_data('jhu')

    if is_new_data(frame, newest_data, 'jhu'):
        global should_tweet
        global should_save_jhu
        should_tweet = True
        should_save_jhu = True
    else:
        logger.warning('Downloaded data is not new! Will not save')

    return frame


def make_state_objects_from_data(data: pd.DataFrame, from_csv=False) -> [State]:
    """
    Creates either a city or state object from a DataFrame
    :param from_csv: Should be true if the data was read in from a CSV to ensure correct column selection. Default false
    :param data: The DataFrame to assemble the object from
    :return: Either a city or state object, depending on what was specified
    """

    city_objs = []
    state_objs = []
    state_names = []

    for name in data['state']:
        if name not in state_names:
            state_names.append(name)

    for name in state_names:
        for row_tuple in data.iterrows():
            # Data read in from a CSV has an index column first, so we just have to shift over 1
            if from_csv:
                row_data = [entry for entry in row_tuple[1]]
                c_name = row_data[2]
                case_dat = row_data[3:6]

                if row_data[1] == name:
                    city_ob = City(city_name=c_name, case_info=case_dat)
                    city_objs.append(city_ob)

            else:
                row_data = [entry for entry in row_tuple[1]]
                c_name = row_data[1]
                case_dat = row_data[2:5]

                if row_data[0] == name:
                    city_ob = City(city_name=c_name, case_info=case_dat)
                    city_objs.append(city_ob)

        state_ob = State(state_name=name, state_cities=city_objs)

        state_objs.append(state_ob)
        city_objs = []

    return state_objs


def get_time_series():
    """
    Reads data from the JHU time series sheet from Github. Presently only gathers info on confirmed cases.
    :return: A dataframe of the time series data for the U.S with columns for the location at which is was discovered
    and a column for each day since tracking began.
    """
    logger.info('Attempting to connect to JHU time series sheet')

    jhu_github_url = 'https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data/csse_covid_19_time_series'
    github_req = requests.get(jhu_github_url)
    git_soup = BeautifulSoup(github_req.content, features='html.parser')

    candidate_link = ''

    for link in git_soup.find_all('a'):
        if link.get('title') == 'time_series_19-covid-Confirmed.csv':
            candidate_link = link.get('href')

    file_link = str('https://raw.githubusercontent.com' + candidate_link).replace('blob/', '')
    newest_csv_req = urllib.request.Request(file_link)
    csv_file = urllib.request.urlopen(newest_csv_req)
    csv_data = csv_file.read()

    with open(jhu_path + 'jhu_time_temp.csv', 'wb') as file:
        file.write(csv_data)

    ts_conf_frame = pd.read_csv(jhu_path + 'jhu_time_temp.csv')
    is_US = ts_conf_frame['Country/Region'] == 'US'
    ts_conf_frame = ts_conf_frame[is_US]
    ts_conf_frame.drop(['Country/Region', 'Lat', 'Long'], axis=1, inplace=True)

    os.remove(jhu_path + 'jhu_time_temp.csv')
    ts_conf_frame.to_csv(jhu_path + 'jhu_time.csv')

    return ts_conf_frame


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


def is_new_data(recent_data: pd.DataFrame, prev_data: pd.DataFrame, source: str):
    """
    Checks to see if the data that was recently fetched is the same as existing data
    :param source: The source of the data. Determines what columns to select. Valid inputs are cdc or jhu
    :param recent_data: The most recently fetched data
    :param prev_data: The dataframe to compare to
    :return: True or false depending on whether or not the recent_data dataframe is newer than the previous one
    """
    columns = []
    # Optional data to return
    cities = []
    states = []
    case_data = []
    cdc_tests = []
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

            # iterrows() returns a tuple of (index, data)
            for tuple_new, tuple_old in zip(recent_data.iterrows(), prev_data.iterrows()):
                # Iterates through each value in the row
                row_data_new = [entry for entry in tuple_new[1]]
                state_new = row_data_new[0]
                city_new = row_data_new[1]
                case_data_new = row_data_new[2:5]

                states_new.append(state_new)
                city_new_data_map[city_new] = case_data_new

                # Data read from a CSV contains an index column, so data values are shifted one to the right
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
            if file != '.DS_Store' or file != 'jhu_time.csv':
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


def make_tweet(topic: str, updates: dict):
    """
    Creates a tweet to post to Twitter
    :param updates: Updates in the data
    :param topic: The data topic to tweet about. Either jhu, cdc, or 'both'
    """

    hashtags = ['#nCoV', '#Coronavirus', '#USCoronavirus', '#2019nCoV', '#COVID19', '#USCOVID19']
    chosen_tags = random.sample(hashtags, k=2)
    text = '2019-nCoV Update: This tracker has found new '
    media_ids = []
    files = ['city_sum.png', 'state_sum.png', 'state_recov.png']

    if topic == 'jhu' or topic == 'both':
        for key in updates.keys():
            if updates[key] != []:
                if text == 'COVID-19: This tracker has found new ':
                    states_format = ''
                    for name in updates[key]:
                        if states_format == '':
                            states_format = name
                        else:
                            states_format = states_format + f' and {name}'
                    text = text + f'{key} in {states_format}'
                else:
                    for name in updates[key]:
                        if states_format == '':
                            states_format = name
                        else:
                            states_format = states_format + f' and {name}'
                    text = text + f', and new {key} in {states_format}'
            states_format = ''

    if text == 'COVID-19 Update: This tracker has found new ':
        text = f'COVID-19 Update: This tracker has found new information from the CDC {chosen_tags[0]}' \
               f' {chosen_tags[1]}'
    else:
        text = text + f' {chosen_tags[0]} {chosen_tags[1]}'

    for file in files:
        response = api.media_upload(plot_path + file)
        media_ids.append(response.media_id)

    print('Sending tweet!')
    logger.info('Found new data! Sending tweet!')

    api.update_status(status=text, media_ids=media_ids)


def get_updated_states(new_data: pd.DataFrame, old_data: pd.DataFrame, old_from_csv=True) -> dict:
    """
    Determines updates to state information
    :param old_from_csv: Was the old data loaded from a CSV? Default is True
    :param old_data: The DataFrame to which the new data will be compared to
    :param new_data: A DataFrame containing state and city data
    :return: A dictionary containing the list of states with new cases, deaths, and recoveries
    """

    new_state_objs = make_state_objects_from_data(new_data)
    old_state_objs = make_state_objects_from_data(old_data, from_csv=old_from_csv)

    new_cases = []
    new_deaths = []
    new_recoveries = []

    for new_state in new_state_objs:
        if new_state.get_name() not in [state.get_name() for state in old_state_objs]:
            if new_state.get_recoveries() > 0:
                new_recoveries.append(new_state.get_name())
            if new_state.get_cases() > 0:
                new_cases.append(new_state.get_name())
            if new_state.get_deaths() > 0:
                new_deaths.append(new_state.get_name())
        else:
            for old_state in old_state_objs:
                if new_state.get_name() == old_state.get_name():
                    if new_state.get_recoveries() > old_state.get_recoveries():
                        new_recoveries.append(new_state.get_name())
                    if new_state.get_cases() > old_state.get_cases():
                        new_cases.append(new_state.get_name())
                    if new_state.get_deaths() > old_state.get_deaths():
                        new_deaths.append(new_state.get_name())

    return {'cases': new_cases, 'deaths': new_deaths, 'recoveries': new_recoveries}


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
              spacer + 'COVID-19 Tracker (U.S)\n',
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
    plt.title('2019-nCoV Cases by City')
    plt.gcf().set_size_inches(10, 10)
    plt.xticks(rotation=45)
    plt.yticks(np.arange(start=0, stop=us_frame['cases'].max() + 1))
    plt.bar(x=us_frame['city'], height=us_frame['cases'])
    plt.xlabel('City')
    plt.ylabel('Confirmed Cases')
    plt.savefig(plot_path + 'city_sum.png')
    plt.show(block=False)
    plt.close()
    # Plot setup for recovery data
    plt.title('2019-nCoV Recoveries by State')
    plt.gcf().set_size_inches(10, 10)
    plt.xticks(rotation=45)
    plt.yticks(np.arange(start=0, stop=us_frame['recoveries'].max() + 1))
    plt.bar(x=us_frame['state'], height=us_frame['recoveries'])
    plt.xlabel('State')
    plt.ylabel('Recoveries')
    plt.savefig(plot_path + 'state_recov.png')
    plt.show(block=False)
    plt.close()

    if should_tweet:
        # File saving had to be moved down here or else the tweet formatter would not be able to detect new data
        old_data = get_most_recent_data('jhu')
        updates = get_updated_states(us_frame, old_data)
        make_tweet('jhu', updates)
        if should_save_jhu:
            print('Found new data! Saving...')
            logger.info('Found new data! Now saving...')
            us_frame.to_csv(jhu_path + 'jhu_' + now_file_ext)

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
