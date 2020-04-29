import os
import time
import logging
import json
import random
import urllib
from datetime import datetime

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
import tweepy as tw
import dataproccessor as dp
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

state_map = {'AL': 'Alabama', 'AK': 'Alaska', 'AR': 'Arkansas', 'AZ': 'Arizona', 'CA': 'California', 'CO': 'Colorado',
             'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii',
             'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky',
             'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan',
             'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska',
             'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
             'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon',
             'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
             'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
             'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming', 'D.C.': 'Washington D.C', 'P.R.': 'Puerto Rico',
             'VI': 'Virgin Islands, U.S.'}

state_abb_map = {}

for name, abb in zip(state_map.values(), state_map.keys()):
    state_abb_map[name] = abb

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

    jhu_github_url = 'https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data/csse_covid_19_daily_reports_us'
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
    us_frame = temp_frame[['Province_State', 'Country_Region', 'Confirmed', 'Deaths', 'Recovered',
                           'Testing_Rate', 'Hospitalization_Rate', 'Incident_Rate', 'Mortality_Rate']]
    us_frame.rename(columns={'Province_State': 'case_loc'}, inplace=True)
    is_US = us_frame['Country_Region'] == 'US'
    us_frame = us_frame[is_US]
    us_frame = us_frame[~us_frame['case_loc'].str.contains('Princess')]

    us_frame = us_frame[['case_loc', 'Confirmed', 'Deaths', 'Recovered', 'Testing_Rate', 'Hospitalization_Rate',
                         'Incident_Rate', 'Mortality_Rate']]
    rename_map = {'case_loc': 'state', 'Confirmed': 'cases', 'Deaths': 'deaths', 'Recovered': 'recoveries',
                  'Testing_Rate': 'test_rate', 'Hospitalization_Rate': 'hosp_rate', 'Incident_Rate': 'incidence',
                  'Mortality_Rate': 'mort_rate'}

    us_frame.rename(columns=rename_map, inplace=True)

    os.remove(jhu_path + 'jhu_temp.csv')

    if us_frame.empty is not True:
        logger.info('Successfully downloaded JHU data! If new will save as jhu_{}'.format(now_file_ext))

    newest_data = get_most_recent_data('jhu')

    if is_new_data(us_frame, newest_data, 'jhu'):
        global should_tweet
        global should_save_jhu
        should_tweet = True
        should_save_jhu = True

        if get_most_recent_data('jhu').empty:
            us_frame.to_csv(jhu_path + 'jhu_' + now_file_ext)
    else:
        logger.warning('Downloaded JHU data is not new! Will not save')

    return us_frame


def make_state_objects_from_data(data: pd.DataFrame, from_csv=False) -> [State]:
    """
    Creates either a city or state object from a DataFrame
    :param from_csv: Should be true if the data was read in from a CSV to ensure correct column selection. Default false
    :param data: The DataFrame to assemble the object from
    :return: Either a city or state object, depending on what was specified
    """

    state_objs = []
    state_names = []
    state_data = make_state_frame(data)

    for name in state_data['state']:
        if name not in state_names:
            state_names.append(name)

    for name in state_names:
        for row_tuple in state_data.iterrows():
            # Data read in from a CSV has an index column first, so we just have to shift over 1
            if from_csv:
                row_data = [entry for entry in row_tuple[1]]
                if row_data[1] == name:
                    case_dat = row_data[2:5]
                    state_ob = State(state_name=name, state_cases=case_dat[0], state_deaths=case_dat[1],
                                     state_recoveries=case_dat[2])

                    state_objs.append(state_ob)
            else:
                row_data = [entry for entry in row_tuple[1]]
                if row_data[0] == name:
                    case_dat = row_data[1:4]
                    state_ob = State(state_name=name, state_cases=case_dat[0], state_deaths=case_dat[1],
                                     state_recoveries=case_dat[2])

                    state_objs.append(state_ob)

    return state_objs


def get_time_series() -> pd.DataFrame:
    """
    Reads data from the JHU time series sheet from Github. Presently only gathers info on confirmed cases.
    :return: A dataframe of the time series data for the U.S with columns for the location at which is was discovered
    and a column for each day since tracking began.
    """

    if os.path.exists(jhu_path + 'jhu_time.csv'):
        data = pd.read_csv(jhu_path + 'jhu_time.csv')
        newest_date = datetime.strptime(data.columns.to_list()[-1], '%m/%d/%y')

        if newest_date == datetime.now().date():
            logger.info('Currently downloaded U.S time series is up to date. Reading file...')

            return data
        else:
            logger.info('Currently downloaded U.S time series may be out of date! Downloading new one...')

            file_link = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv'
            newest_csv_req = urllib.request.Request(file_link)
            csv_file = urllib.request.urlopen(newest_csv_req)
            csv_data = csv_file.read()

            with open(jhu_path + 'jhu_time_temp.csv', 'wb') as file:
                file.write(csv_data)

            ts_conf_frame = pd.read_csv(jhu_path + 'jhu_time_temp.csv')
            is_US = ts_conf_frame['Country/Region'] == 'US'
            ts_conf_frame = ts_conf_frame[is_US]

            ts_conf_frame.drop(['Country/Region', 'Lat', 'Long'], axis=1, inplace=True)
            ts_conf_frame.rename(columns={'Province/State': 'state'}, inplace=True)

            logger.info('Removing JHU temp file...')
            os.remove(jhu_path + 'jhu_time_temp.csv')
            ts_conf_frame.to_csv(jhu_path + 'jhu_time.csv')
            logger.info('Saved time series data successfully!')

            return ts_conf_frame
    else:
        logger.info('Attempting to download JHU time series sheet')

        file_link = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv'
        newest_csv_req = urllib.request.Request(file_link)
        csv_file = urllib.request.urlopen(newest_csv_req)
        csv_data = csv_file.read()

        with open(jhu_path + 'jhu_time_temp.csv', 'wb') as file:
            file.write(csv_data)

        ts_conf_frame = pd.read_csv(jhu_path + 'jhu_time_temp.csv')
        is_US = ts_conf_frame['Country/Region'] == 'US'
        ts_conf_frame = ts_conf_frame[is_US]

        ts_conf_frame.drop(['Country/Region', 'Lat', 'Long'], axis=1, inplace=True)
        ts_conf_frame.rename(columns={'Province/State': 'state'}, inplace=True)

        logger.info('Removing JHU temp file...')
        os.remove(jhu_path + 'jhu_time_temp.csv')
        ts_conf_frame.to_csv(jhu_path + 'jhu_time.csv')
        logger.info('Saved time series data successfully!')

        return ts_conf_frame


def get_daily_change(time_data: pd.DataFrame, country='default', change_type='cases') -> int:
    """
    Calculate the daily change in cases for a country from time series data
    :param change_type: What type of changes should be calculated. Default is cases. Valid types are cases and deaths
    :param country: The country of interest. Valid inputs are default (Assumes that the provided data only comes from a
    single country) or the name of a country
    :param time_data: The JHU time series DataFrame
    :return: The difference in cases between the most recent day and the one before it
    """

    # Select for columns for a /20 as those contain dates
    if country != 'default':
        is_country = time_data['Country/Region'] == country
        country_data = time_data[is_country]
        valid_columns = [column for column in country_data.columns.to_list() if '/20' in column]
        valid_data = country_data[valid_columns]
    else:
        valid_columns = [column for column in time_data.columns.to_list() if '/20' in column]
        valid_data = time_data[valid_columns]

    newest_column_date = valid_data.columns.to_list()[-1:]
    prev_column_date = valid_data.columns.to_list()[-2:-1]

    newest_column_sum = valid_data[newest_column_date].sum()
    prev_column_sum = valid_data[prev_column_date].sum()

    # Since there is no data behind the first date, default to 0
    try:
        int(prev_column_sum)
    except TypeError:
        prev_column_sum = 0

    return int(newest_column_sum) - int(prev_column_sum)



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

            # iterrows() returns a tuple of (index, data)
            for tuple_new, tuple_old in zip(recent_data.iterrows(), prev_data.iterrows()):
                # Iterates through each value in the row
                row_data_new = [entry for entry in tuple_new[1]]
                state_new = row_data_new[0]
                case_data_new = row_data_new[1:4]

                states_new.append(state_new)

                # Data read from a CSV contains an index column, so data values are shifted one to the right
                row_data_old = [entry for entry in tuple_old[1]]
                state_old = row_data_old[1]
                case_data_old = row_data_old[2:5]

                states_old.append(state_old)

            if states_new.sort() != states_old.sort():
                is_new = True
            if case_data_old != case_data_new:
                is_new = True

        return is_new


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
            if file != '.DS_Store' and 'time' not in file:
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

    hashtags = ['#Coronavirus', '#USCoronavirus', '#COVID19', '#USCOVID19', '#CoronaOutbreak', '#CoronaAlert',
                '#COVID_19', '#CoronaPandemic', '#CoronavirusOutbreak']
    chosen_tags = random.sample(hashtags, k=3)
    lead_media_ids = []
    follow_media_ids = []
    lead_files = ['capita_plot.png', 'capita_rate.png', 'death_comp_plot.png', 'change_plot.png']
    follow_files = ['comp_plot.png', 'state_sum.png', 'rate_plot.png']

    ts_data = get_time_series()
    global_ts = dp.get_global_time_series()
    change = get_daily_change(ts_data)
    prev_column = ts_data.columns.to_list()[-2]
    percent_change = round((change / ts_data[prev_column].sum()) * 100, 2)

    us_death_ts = dp.get_death_time_series('US')
    death_prev_col = us_death_ts.columns.to_list()[-1]
    death_change = get_daily_change(us_death_ts)
    percent_death_change = round((death_change / us_death_ts[death_prev_col].sum()) * 100, 2)

    prev_column_comp = global_ts.columns.to_list()[-1]
    us_global_share = round((dp.get_country_cumulative(ts_data)[-1] / global_ts[prev_column_comp].sum()) * 100, 2)
    target = 1100000

    time_to_target = dp.get_time_to_target(target)

    top_3_per_cap_pairs = dp.get_deaths_per_capita(size=3)
    top_3_per_cap = [entry[0] for entry in top_3_per_cap_pairs]

    text = f'COVID-19 Update: This tracker has found {change:,} new cases and {death_change:,} new deaths, ' \
           f'a {percent_change}% increase in cases and {percent_death_change}% increase in deaths since yesterday. ' \
           f"The top 3 states in deaths per 100,000 population are {top_3_per_cap[0]}, {top_3_per_cap[1]}, and" \
           f" {top_3_per_cap[2]}"

    follow_text = f"The U.S currently has {us_global_share}% of the world's cases. At its 3-day average rate, " \
                  f"the U.S will have {target:,} cases in {time_to_target} days (Estimate)." \
                  f" {chosen_tags[0]} {chosen_tags[1]} {chosen_tags[2]}"

    multi_tweet = True

    print(text)
    print(follow_text)

    for file in lead_files:
        response = api.media_upload(plot_path + file)
        lead_media_ids.append(response.media_id)
    for file in follow_files:
        response = api.media_upload(plot_path + file)
        follow_media_ids.append(response.media_id)

    print('Sending tweet!')
    logger.info('Found new data! Sending tweet!')

    if multi_tweet:
        lead_tweet = api.update_status(status=text, media_ids=lead_media_ids)
        api.update_status(status=follow_text, in_reply_to_status_id=lead_tweet.id, media_ids=follow_media_ids)
    else:
        api.update_status(status=text, media_ids=lead_media_ids)


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

    dp.make_plots([us_frame, get_time_series(), dp.get_global_time_series()])

    if should_tweet:
        # File saving had to be moved down here or else the tweet formatter would not be able to detect new data
        old_data = get_most_recent_data('jhu')
        updates = get_updated_states(us_frame, old_data)
        make_tweet('change', updates)
        if should_save_jhu:
            print('Found new JHU data! Saving...')
            logger.info('Found new JHU data! Now saving...')
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
