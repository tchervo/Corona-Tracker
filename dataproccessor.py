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
    width = 0.9
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

    make_state_death_plot()

    make_per_capita_plot()

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


# Needs some improvements to polynomial fitting - Temporarily disabled
def make_acceleration_plot():
    changes = get_total_daily_change(ct.get_time_series())[50:]
    x_vals = np.arange(start=1, stop=len(changes) + 1)
    coeff = np.polynomial.polynomial.polyfit(x=x_vals, y=changes, deg=2)
    print(coeff)
    change_rate = [((2 * coeff[2]) * x) + coeff[1] for x in x_vals]
    fitted = [(coeff[2] * (x ** 2) + (coeff[1] * x)) + coeff[0] for x in x_vals]

    plt.plot(x_vals, change_rate, color='red')
    # plt.plot(x_vals, fitted, color='green')
    # plt.plot(x_vals, changes, color='blue')

    plt.show()
    plt.close()


def get_country_cumulative(data: pd.DataFrame, countries='US') -> list:
    """
    Calculates the cumulative of new cases for the U.S or a selected group of countries each day
    :param countries: Either a single country or a list of countries 
    :param data: A DataFrame containing time series data for cases
    :return: A list of the number of cases for each day
    """

    if countries == 'US':
        rates = [data[column].tolist() for column in data.columns if '/20' in column]
        daily_rates = [np.sum(day_rate) for day_rate in rates]

        return daily_rates
    elif type(countries) is list:
        cumulative_cases = []

        for country in countries:
            is_country = data['Country_Region'] == country
            country_frame = data[is_country]

            rates = [country_frame[column].tolist() for column in country_frame.columns if '/20' in column]
            daily_rates = [np.sum(day_rate) for day_rate in rates]

            cumulative_cases.append(daily_rates)

        return cumulative_cases
    else:
        is_country = data['Country_Region'] == countries
        country_frame = data[is_country]

        rates = [country_frame[column].tolist() for column in country_frame.columns if '/20' in column]
        daily_rates = [np.sum(day_rate) for day_rate in rates]

        return daily_rates


def get_total_daily_change(data: pd.DataFrame, country='US') -> list:
    """
    Calculates the change in either cases or deaths for each day since the time first recorded in the data
    :param country: The country to get the changes for. Default is US
    :param data: a DataFrame containing time series data
    :return: The change in cases for each day
    """
    if country == 'US':
        # Select columns with dates
        columns = [column for column in data.columns.to_list() if '/20' in column]
        changes = []

        for index in range(0, len(columns)):
            if index != len(columns):
                index = index + 1
                needed_columns = columns[:index]
                changes.append(ct.get_daily_change(data[needed_columns]))
            else:
                changes.append(ct.get_daily_change(data))

        return changes
    else:
        country_data = data[data['Country_Region'] == country]
        columns = [column for column in country_data.columns.to_list() if '/20' in column]
        changes = []
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
            global_frame.rename(columns={'Province/State': 'Province_State', 'Country/Region': 'Country_Region'},
                                inplace=True)
            global_frame.to_csv(ct.jhu_path + 'jhu_global_time.csv')
            os.remove(ct.jhu_path + 'jhu_global_time_temp.csv')

            ct.logger.info('Succesfully downloaded time series data!')

            return global_frame

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


def get_death_time_series(country='all') -> pd.DataFrame:
    """
    Downloads the global deaths time series. Can return for a specific country or all countries
    :param: country: Either 'all' for all countries or a specific country's name. Default is all.
    :return: A DataFrame containing the death time series for a given country or all countries
    """

    if country == 'US':
        file_path = ct.jhu_path + 'jhu_death_time_us.csv'
        file_link = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv'
        drop_list = ['UID', 'iso2', 'iso3', 'code3', 'FIPS', 'Lat', 'Long_', 'Combined_Key']
    else:
        file_path = ct.jhu_path + 'jhu_death_time_global.csv'
        file_link = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv'
        drop_list = ['Lat', 'Long']

    if os.path.exists(file_path):
        data = pd.read_csv(file_path)
        newest_date = datetime.strptime(data.columns.to_list()[-1], '%m/%d/%y')

        if newest_date == datetime.now().date():
            ct.logger.info('Currently downloaded global death time series is up to date. Reading file...')

            return data
        else:
            ct.logger.info('Global death time series data may be out of date! Trying to download new file...')

            newest_csv_req = urllib.request.Request(file_link)
            csv_file = urllib.request.urlopen(newest_csv_req)
            csv_data = csv_file.read()

            with open(ct.jhu_path + 'jhu_time_temp.csv', 'wb') as file:
                file.write(csv_data)

            death_frame = pd.read_csv(ct.jhu_path + 'jhu_time_temp.csv')

            death_frame.drop(columns=drop_list, inplace=True)
            death_frame.to_csv(file_path)
            os.remove(ct.jhu_path + 'jhu_time_temp.csv')

            ct.logger.info('Succesfully downloaded death time series data!')

            # JHU has some inconsistencies in column naming, so here we patch them up
            if country == 'all':
                death_frame.rename(columns={'Province/State': 'Province_State', 'Country/Region':
                    'Country_Region'}, inplace=True)
                return death_frame
            elif country == 'US':
                death_frame.rename(columns={'Admin2': 'City_County'}, inplace=True)
                return death_frame
            else:
                death_frame.rename(columns={'Province/State': 'Province_State', 'Country/Region':
                    'Country_Region'}, inplace=True)
                return death_frame[death_frame['Country_Region'] == country]

    ct.logger.info('Global death time series data may be out of date! Trying to download new file...')

    newest_csv_req = urllib.request.Request(file_link)
    csv_file = urllib.request.urlopen(newest_csv_req)
    csv_data = csv_file.read()

    with open(ct.jhu_path + 'jhu_time_temp.csv', 'wb') as file:
        file.write(csv_data)

    death_frame = pd.read_csv(ct.jhu_path + 'jhu_time_temp.csv')

    death_frame.drop(columns=drop_list, inplace=True)
    death_frame.to_csv(file_path)
    os.remove(ct.jhu_path + 'jhu_time_temp.csv')

    ct.logger.info('Succesfully downloaded death time series data!')

    if country == 'all':
        return death_frame
    elif country == 'US':
        death_frame.rename(columns={'Admin2': 'City_County'}, inplace=True)
        return death_frame
    else:
        return death_frame[death_frame['Country_Region'] == country]


def find_metric_leader(global_data: pd.DataFrame, inc_US=False) -> str:
    """
    Finds the country with the largest amount of cases or deaths, depending on the type of data provided
    :param inc_US: Should the U.S be included as a potential leader? Default is no due to the U.S' current position
    :param global_data: Global time series data
    :return: The name of the leading country
    """

    current_leader = 'NO COUNTRY FOUND'
    leader_cases = 0

    for country in global_data['Country_Region']:
        if country == 'US' and inc_US is False:
            pass
        else:
            country_data = global_data[global_data['Country_Region'] == country]
            last_column_name = country_data.columns.to_list()[-1]
            total_cases = country_data[last_column_name].sum()

            if total_cases > leader_cases:
                current_leader = country
                leader_cases = total_cases

    return current_leader


def get_time_to_target(target=-1, metric_type='cases'):
    """
    Tries to find the amount of time in days it will take for the U.S to arrive at the target number of cases based on
    the mean change in cases over the past five days
    :param metric_type: The target type. Either cases or deaths
    :param target: The target number of cases if using cases.
    :return:
    """

    if metric_type == 'cases':
        if target == -1:
            raise ValueError('Must specify a target if type is set to cases!')

        # Since the U.S is now the leader in cases, the time to leader mode for cases has been disabled
        # Slope is calculated from the past three days to prevent skew from earlier time periods
        us_changes = get_total_daily_change(ct.get_time_series())[-3:]
        us_slope = np.mean(us_changes)
        # leader = find_case_leader(global_data)
        # leader_changes = get_total_daily_change(global_data, 'China')[-5:]
        # leader_slope = np.mean(leader_changes)

        est_us_cases = get_country_cumulative(ct.get_time_series())[-1]
        # est_leader_cases = get_country_cumulative(get_global_time_series(), countries=leader)[-1]

        add_days = 0

        while est_us_cases <= target:
            add_days += 0.1
            est_us_cases += us_slope * 0.1

        return round(add_days, 2)
    if metric_type == 'deaths':
        # Slope is calculated from the past three days to prevent skew from earlier time periods
        us_changes = get_total_daily_change(get_death_time_series('US'))[-3:]
        us_slope = np.mean(us_changes)
        leader = find_metric_leader(get_death_time_series())
        leader_changes = get_total_daily_change(get_death_time_series(country=leader), leader)[-3:]
        leader_slope = np.mean(leader_changes)

        est_us_deaths = get_country_cumulative(get_death_time_series('US'))[-1]
        est_leader_deaths = get_country_cumulative(get_death_time_series(leader), countries=leader)[-1]

        add_days = 0

        if leader_slope > us_slope:
            return -1
        else:
            while est_us_deaths <= est_leader_deaths:
                add_days += 0.1
                est_us_deaths += us_slope * 0.1
                est_leader_deaths += leader_slope * 0.1

            return round(add_days, 2)


def get_top_states_by_metric(metric: str, size: int) -> [str]:
    """
    Gets the top number of states by a certain metric, either cases or deaths
    :param metric: Either cases or deaths
    :param size: The number of entries to return
    :return: A list of size 'size' containing the top states for that metric
    """

    if metric == 'cases':
        data = ct.get_time_series()
    elif metric == 'deaths':
        data = get_death_time_series('US')
    else:
        raise ValueError("'metric' must be either 'cases' or 'deaths'!")

    most_recent_column = data.columns.to_list()[-1]
    states = []

    data.sort_values(ascending=False, by=most_recent_column, inplace=True)

    for state in data['Province_State']:
        if state not in states and len(states) <= size:
            states.append(state)
        if len(states) == size:
            break

    return states


def make_state_death_plot():
    """
    Creates a line plot of the cumulative death total for the top five U.S states
    """

    death_data = get_death_time_series('US')
    states = get_top_states_by_metric('deaths', 5)
    state_counts = []
    most_recent_column = death_data.columns.to_list()[-1]
    relevant_columns = [column for column in death_data.columns.to_list() if '/20' in column]

    for state in states:
        state_data = death_data[death_data['Province_State'] == state]
        state_data = state_data[relevant_columns]
        internal_counts = []

        for column in state_data.columns:
            day_sum = int(state_data[column].sum())

            internal_counts.append(day_sum)

        state_counts.append(internal_counts)
        internal_counts = []

    # Finally start setting up the plot
    days = len(relevant_columns) + 1
    x_vals = np.arange(start=1, stop=days)

    plt.title(f'Daily Death Totals for the Top 5 U.S States by Death Total On {most_recent_column}')
    plt.xlabel('Days Since 01/22/2020')
    plt.ylabel('Deaths')
    plt.gcf().set_size_inches(12, 12)

    line_1 = plt.plot(x_vals, state_counts[0], color='red')
    line_2 = plt.plot(x_vals, state_counts[1], color='green')
    line_3 = plt.plot(x_vals, state_counts[2], color='blue')
    line_4 = plt.plot(x_vals, state_counts[3], color='orange')
    line_5 = plt.plot(x_vals, state_counts[4], color='purple')

    plt.legend((line_1[0], line_2[0], line_3[0], line_4[0], line_5[0]),
               (states[0], states[1], states[2], states[3], states[4]),
               loc='upper left')

    plt.savefig(ct.plot_path + 'death_comp_plot.png')
    plt.show(block=False)
    plt.close()


def get_deaths_per_capita(multiplier=100000, size=5) -> list:
    """
    Gets the top n U.S states per multiplier
    :param multiplier: The multipler to use for the resulting rate. As in 'X deaths per {metric}'
    :param size: The number of states to return. Default is five
    :return: A list of the top {n} states per {multiplier}
    """

    death_data = get_death_time_series('US')
    most_recent_column = death_data.columns.to_list()[-1]
    states = []
    combinations = []

    for state in death_data['Province_State']:
        if state not in states:
            states.append(state)

    for state in states:
        state_frame = death_data[death_data['Province_State'] == state]
        total_pop = int(state_frame['Population'].sum())
        total_deaths = int(state_frame[most_recent_column].sum())

        if total_pop == 0:
            pass
        else:
            # Per 100,000
            death_rate = round((total_deaths / total_pop) * multiplier, 2)

            combinations.append((state, death_rate))

    top_list = sorted(combinations, key=lambda state_pair: state_pair[1], reverse=True)

    return top_list[:size]


def make_per_capita_plot():
    """
    Makes a plot of the top five states per capita by deaths
    """

    top_5 = get_deaths_per_capita()

    # Now for the plotting
    plot_states = [entry[0] for entry in top_5]
    plot_rates = [entry[1] for entry in top_5]

    plt.gcf().set_size_inches(10, 10)
    plt.title(f'Top 5 States by Deaths per 100,000 Population on {ct.now.strftime("%m/%d/%y")}')
    plt.xlabel('State')
    plt.ylabel('Deaths per 100,000 Population')
    plt.bar(x=plot_states, height=plot_rates)

    plt.savefig(ct.plot_path + 'capita_plot.png')
    plt.show(block=False)
    plt.close()
