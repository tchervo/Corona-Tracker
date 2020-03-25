import math

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

    plt.title('Daily Change in Cases Since 01/22/2020')
    plt.xlabel('Days since 01/22/2020')
    plt.ylabel('Change in Cases from Previous Day')

    plt.plot(np.arange(1, stop=days), changes, color='red')

    plt.savefig(ct.plot_path + 'change_plot.png')
    plt.show(block=False)
    plt.close()


def get_country_cumulative(data: pd.DataFrame) -> list:
    """
    Calculates the cumulative of new cases for the U.S each day
    :param data: A DataFrame containing time series data for cases
    :return: A list of the number of cases for each day
    """

    rates = [data[column].tolist() for column in data.columns if column != 'state' and column != 'city']
    daily_rates = [np.sum(day_rate) for day_rate in rates]

    return daily_rates


def get_total_daily_change(data: pd.DataFrame, from_csv=False) -> list:
    """
    Calculates the change for each day since the time first recorded in the data
    :param data: a DataFrame containing time series data
    :return: The change in cases for each day
    """
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
