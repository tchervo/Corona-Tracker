import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import coronatracker as ct


def make_plots(data: [pd.DataFrame]):
    """
    Generates the plots displayed in tweets posted by this bot.
    :param data: A list of DataFrames. The first frame should contain all the JHU data for the U.S, and the second
    frame should contain all the information for the CDC
    """
    print('Attempting to build plots!')
    ct.logger.info('Making plots...')

    us_frame = data[0]
    has_many_cases = us_frame.cases > 2
    # Only contains cities with a certain number of cases to reduce crowding
    opt_city_frame = us_frame[has_many_cases]
    # cdc_frame = data[1]

    # General Plot Setup. Plots are "shown" then immediately closed to refresh the figure
    plt.style.use('fivethirtyeight')

    for jhu_tick in plt.xticks()[1]:
        jhu_tick.set_rotation(45)

    plt.suptitle('COVID-19 Details for the United States')
    # Plot setup for CDC figure
    # cdc_ax.bar(x=cdc_frame['measure'], height=cdc_frame['counts'])
    # cdc_ax.set_xlabel('Test Result')
    # cdc_ax.set_ylabel('Count')
    # cdc_ax.set_title('U.S COVID-19 Cases and Transmission Route')
    # Plot setup for JHU figure
    state_frame = ct.make_state_frame(us_frame)
    pos = np.arange(len(state_frame['state']))
    width = 0.7
    # Interval is [Start, Stop) so we need to go one more
    plt.gcf().set_size_inches(12, 12)
    plt.yticks(np.arange(start=0, stop=state_frame['cases'].max() + 1, step=5))
    case_bar = plt.bar(pos, state_frame['cases'], width, label='Cases')
    death_bar = plt.bar(pos, state_frame['deaths'], width, label='Deaths')
    recov_bar = plt.bar(pos, state_frame['recoveries'], width,
                         bottom=state_frame['deaths'], label='Recoveries')

    plt.xlabel('State')
    plt.ylabel('Count')
    plt.title('Confirmed COVID-19 Case Statistics in the United States by State with >2 Cases')
    plt.xticks(pos, state_frame['state'].tolist(), fontsize=10)
    plt.legend((case_bar[0], death_bar[0], recov_bar[0]), ('Cases', 'Deaths', 'Recoveries'), loc='upper right')
    plt.savefig(ct.plot_path + 'state_sum.png')
    plt.show(block=False)
    plt.close()
    # Plot setup for city data
    plt.title('COVID-19 Cases by City with >2 Cases')
    plt.gcf().set_size_inches(12, 16)
    pos_city = np.arange(len(opt_city_frame['city']))
    plt.yticks(np.arange(start=0, stop=opt_city_frame['cases'].max() + 1, step=5))
    city_case = plt.bar(pos_city, opt_city_frame['cases'], width, label='City Cases')
    city_death = plt.bar(pos_city, opt_city_frame['deaths'], width, label='City Deaths')
    city_recov = plt.bar(pos_city, opt_city_frame['recoveries'], width, label='City Recoveries', bottom=opt_city_frame['deaths'])
    plt.xticks(pos_city, opt_city_frame['city'].tolist(), fontsize=10, rotation=45)
    plt.legend((city_case[0], city_death[0], city_recov[0]), ('Cases', 'Deaths', 'Recoveries'), loc='best')
    plt.xlabel('City')
    plt.ylabel('Count')
    plt.savefig(ct.plot_path + 'city_sum.png')
    plt.show(block=False)
    plt.close()

    ct.logger.info('Created plots!')
