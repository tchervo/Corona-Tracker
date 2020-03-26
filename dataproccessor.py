import math
import urllib
import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import coronatracker as ct


def make_plots(data: [pd.DataFrame]):
    """
    Generates the plots displayed in tweets posted by this bot.
    :param data: A list of DataFrames. The first frame should contain all the JHU data for the U.S, and the second
    frame should contain time series information.
    """
    print('Attempting to build plots!')
    ct.logger.info('Making plots...')

    us_frame = data[0]
    ts_data = data[1]
    global_data = data[2]
    # Select the top 25 states
    us_frame.sort_values(by='cases', axis=0, ascending=False, inplace=True)

    # General Plot Setup. Plots are "shown" then immediately closed to refresh the figure
    plt.style.use('fivethirtyeight')

    for jhu_tick in plt.xticks()[1]:
        jhu_tick.set_rotation(45)

    plt.suptitle('COVID-19 Details for the United States')

    # Plot setup for JHU figure
    state_frame = ct.make_state_frame(us_frame)
    state_frame = state_frame.iloc[np.arange(0, 26), [0, 1, 2, 3]]

    pos = np.arange(len(state_frame['state']))
    width = 0.7
    # Interval is [Start, Stop) so we need to go one more
    plt.gcf().set_size_inches(14, 14)

    # Tries to find a visually appealing number of y ticks
    jhu_step = 50
    while len(np.arange(start=state_frame['cases'].min(), stop=state_frame['cases'].max() + 1, step=jhu_step)) > 34:
        jhu_step += 10

    plt.yticks(np.arange(start=state_frame['cases'].min(), stop=state_frame['cases'].max() + 1, step=jhu_step))
    case_bar = plt.bar(pos, state_frame['cases'], width, label='Cases')
    death_bar = plt.bar(pos, state_frame['deaths'], width, label='Deaths')
    recov_bar = plt.bar(pos, state_frame['recoveries'], width,
                        bottom=state_frame['deaths'], label='Recoveries')

    plt.xlabel('State')
    plt.ylabel('Count')
    plt.title(f'Confirmed COVID-19 Case Statistics for the Top 25 States by Caseload')
    plt.xticks(pos, state_frame['state'].tolist(), fontsize=10)
    plt.legend((case_bar[0], death_bar[0], recov_bar[0]), ('Cases', 'Deaths', 'Recoveries'), loc='upper right')
    plt.savefig(ct.plot_path + 'state_sum.png')
    plt.show(block=False)
    plt.close()

    # Time Series Cumulative Plot
    freqs = get_country_cumulative(ts_data)
    make_time_series_plot(freqs)

    # Daily Change Plot
    changes = get_total_daily_change(ts_data)
    make_daily_change_plot(changes)

    # Country Cumulative Case Comparison Plot
    cumulative_cases = get_country_cumulative(global_data, countries=['US', 'Italy', 'Spain', 'Germany',
                                                                      'Canada', 'United Kingdom', 'China'])

    make_comparison_plot(cumulative_cases)

    ct.logger.info('Created plots!')


def make_time_series_plot(freqs: list):
    """
    Creates a simple line plot of the number of cases for each day of the outbreak
    :param freqs: The number of cases for each day of the outbreak
    """

    days = len(freqs)
    fig, (reg_ax, log_ax) = plt.subplots(1, 2)

    fig.set_size_inches(12, 10)

    fig.suptitle('Cumulative Cases per Day in the United States (Standard Scale and Natural Log)')

    reg_ax.plot(np.arange(start=1, stop=days + 1), freqs, color='red')
    reg_ax.set_xlabel('Days Since 01/21/2020')
    reg_ax.set_ylabel('Number of cases')

    log_freqs = [math.log(freq) for freq in freqs]

    log_ax.plot(np.arange(start=1, stop=days + 1), log_freqs, color='red')
    log_ax.set_xlabel('Days Since 01/21/2020')
    log_ax.set_ylabel('Number of cases (Natural Log Scale)')

    plt.savefig(ct.plot_path + 'rate_plot.png')
    plt.show(block=False)
    plt.close()


def make_daily_change_plot(changes: []):
    """
    Plots the daily change in cases
    :param changes: A list of the changes that have occured each day
    """

    # Plus 1 because numpy stops 1 before the max value
    days = len(changes) + 1

    plt.plot(np.arange(1, stop=days), changes, color='red')

    plt.title('Daily Change in Cases Since 01/22/2020')
    plt.gcf().set_size_inches(12, 12)
    plt.xlabel('Days since 01/22/2020')
    plt.ylabel('Change in Cases from Previous Day')

    plt.savefig(ct.plot_path + 'change_plot.png')
    plt.show(block=False)
    plt.close()


def make_comparison_plot(cumulative_cases: list):
    """Creates a line plot comparing U.S Cumulative Cases to other countries"""

    countries = ['US', 'Italy', 'Spain', 'Germany', 'Canada', 'United Kingdom', 'China']
    change_dict = {country: change for country, change in zip(countries, cumulative_cases)}

    days = len(change_dict['US']) + 1

    us_line = plt.plot(np.arange(1, stop=days), change_dict['US'], color='red')
    italy_line = plt.plot(np.arange(1, stop=days), change_dict['Italy'], color='blue')
    spain_line = plt.plot(np.arange(1, stop=days), change_dict['Spain'], color='green')
    germany_line = plt.plot(np.arange(1, stop=days), change_dict['Germany'], color='purple')
    canada_line = plt.plot(np.arange(1, stop=days), change_dict['Canada'], color='orange')
    uk_line = plt.plot(np.arange(1, stop=days), change_dict['United Kingdom'], color='yellow')
    china_line = plt.plot(np.arange(1, stop=days), change_dict['China'], color='black')

    plt.legend((us_line[0], italy_line[0], spain_line[0], germany_line[0], canada_line[0], uk_line[0], china_line[0]),
               ('United States', 'Italy', 'Spain', 'Germany', 'Canada', 'United Kingdom', 'China'),
               loc='upper left')

    plt.title('Cumulative Cases in the U.S and Other Countries')
    plt.gcf().set_size_inches(12, 12)
    plt.xlabel('Days since 01/22/2020')
    plt.ylabel('Cumulative Cases')

    plt.savefig(ct.plot_path + 'comp_plot.png')
    plt.show(block=False)
    plt.close()


def get_country_cumulative(data: pd.DataFrame, countries='US') -> list:
    """
    Calculates the cumulative of new cases for the U.S or a selected group of countries each day
    :param countries: Either a single country or a list of countries 
    :param data: A DataFrame containing time series data for cases
    :return: A list of the number of cases for each day
    """

    if countries == 'US':
        rates = [data[column].tolist() for column in data.columns if column != 'state' and column != 'city']
        daily_rates = [np.sum(day_rate) for day_rate in rates]

        return daily_rates
    elif type(countries) is list:
        cumulative_cases = []

        for country in countries:
            is_country = data['Country/Region'] == country
            country_frame = data[is_country]

            rates = [country_frame[column].tolist() for column in country_frame.columns if column != 'Province/State'
                     and column != 'Country/Region']
            daily_rates = [np.sum(day_rate) for day_rate in rates]

            cumulative_cases.append(daily_rates)

        return cumulative_cases
    else:
        is_country = data['Country/Region'] == countries
        country_frame = data[is_country]

        rates = [country_frame[column].tolist() for column in country_frame.columns if column != 'Province/State'
                 and column != 'Country/Region']
        daily_rates = [np.sum(day_rate) for day_rate in rates]

        return daily_rates


def get_total_daily_change(data: pd.DataFrame, country='US') -> list:
    """
    Calculates the change for each day since the time first recorded in the data
    :param country: The country to get the changes for. Default is US
    :param data: a DataFrame containing time series data
    :return: The change in cases for each day
    """
    if country == 'US':
        columns = data.columns.to_list()
        changes = []

        for index in range(3, len(columns)):
            if index != len(columns):
                index = index + 1
                needed_columns = columns[2:index]
                changes.append(ct.get_daily_change(data[needed_columns]))
            else:
                changes.append(ct.get_daily_change(data))

        return changes
    else:
        country_data = data[data['Country/Region'] == country]
        columns = country_data.columns.to_list()
        changes = []

        for index in range(3, len(columns)):
            if index != len(columns):
                index = index + 1
                needed_columns = columns[2:index]
                changes.append(ct.get_daily_change(country_data[needed_columns]))
            else:
                changes.append(ct.get_daily_change(country_data))

        return changes


def get_global_time_series() -> pd.DataFrame:
    """Downloads and saves the time series file without filtering for only U.S data"""

    if os.path.exists(ct.jhu_path + 'jhu_global_time.csv'):
        data = pd.read_csv(ct.jhu_path + 'jhu_global_time.csv')
        newest_date = datetime.strptime(data.columns.to_list()[-1], '%m/%d/%y')

        if newest_date == datetime.now().date():
            ct.logger.info('Currently downloaded global time series is up to date. Reading file...')

            return data
        else:
            ct.logger.info('Global time series data may be out of date! Trying to download new file...')
            file_link = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv'

            newest_csv_req = urllib.request.Request(file_link)
            csv_file = urllib.request.urlopen(newest_csv_req)
            csv_data = csv_file.read()

            with open(ct.jhu_path + 'jhu_global_time_temp.csv', 'wb') as file:
                file.write(csv_data)

            global_frame = pd.read_csv(ct.jhu_path + 'jhu_global_time_temp.csv')

            global_frame.drop(columns=['Lat', 'Long'], inplace=True)
            global_frame.to_csv(ct.jhu_path + 'jhu_global_time.csv')
            os.remove(ct.jhu_path + 'jhu_global_time_temp.csv')

            ct.logger.info('Succesfully downloaded time series data!')

            return global_frame

    ct.logger.info('Trying to download global time series data...')
    file_link = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv'

    newest_csv_req = urllib.request.Request(file_link)
    csv_file = urllib.request.urlopen(newest_csv_req)
    csv_data = csv_file.read()

    with open(ct.jhu_path + 'jhu_global_time_temp.csv', 'wb') as file:
        file.write(csv_data)

    global_frame = pd.read_csv(ct.jhu_path + 'jhu_global_time_temp.csv')

    global_frame.drop(columns=['Lat', 'Long'], inplace=True)
    global_frame.to_csv(ct.jhu_path + 'jhu_global_time.csv')
    os.remove(ct.jhu_path + 'jhu_global_time_temp.csv')

    ct.logger.info('Succesfully downloaded time series data!')

    return global_frame


def find_case_leader(global_data: pd.DataFrame) -> str:
    """
    Finds the country with the largest amount of cases
    :param global_data: Global time series data
    :return: The name of the leading country
    """

    current_leader = 'NO COUNTRY FOUND'
    leader_cases = 0

    for country in global_data['Country/Region']:
        country_data = global_data[global_data['Country/Region'] == country]
        last_column_name = country_data.columns.to_list()[-1]
        total_cases = country_data[last_column_name].sum()

        if total_cases > leader_cases:
            current_leader = country
            leader_cases = total_cases

    return current_leader


def get_time_to_leader(global_data: pd.DataFrame):
    """
    Tries to find the amount of time in days it will take for the U.S to overtake the current case leader based on
    the mean change in cases over the past five days
    :param global_data:
    :return:
    """

    us_changes = get_total_daily_change(ct.get_time_series())[-5:]
    us_slope = np.mean(us_changes)
    leader = find_case_leader(global_data)
    leader_changes = get_total_daily_change(global_data, 'China')[-5:]
    leader_slope = np.mean(leader_changes)

    est_us_cases = get_country_cumulative(ct.get_time_series())[-1]
    est_leader_cases = get_country_cumulative(get_global_time_series(), countries=leader)[-1]

    add_days = 0

    while est_us_cases <= est_leader_cases:
        add_days += 1
        est_us_cases += us_slope
        est_leader_cases += leader_slope

    return add_days
