import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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
    cdc_frame = data[1]

    # General Plot Setup. Plots are "shown" then immediately closed to refresh the figure
    plt.style.use('fivethirtyeight')
    fig, (jhu_ax, cdc_ax) = plt.subplots(1, 2, figsize=(20, 22))

    for jhu_tick, cdc_tick in zip(jhu_ax.get_xticklabels(), cdc_ax.get_xticklabels()):
        jhu_tick.set_rotation(45)
        cdc_tick.set_rotation(45)
        cdc_tick.set_fontsize('small')

    fig.suptitle('COVID-19 Details for the United States')
    # Plot setup for CDC figure
    cdc_ax.bar(x=cdc_frame['measure'], height=cdc_frame['counts'])
    cdc_ax.set_xlabel('Test Result')
    cdc_ax.set_ylabel('Count')
    cdc_ax.set_title('U.S COVID-19 Cases and Transmission Route')
    # Plot setup for JHU figure
    state_frame = ct.make_state_frame(us_frame)
    # Interval is [Start, Stop) so we need to go one more
    jhu_ax.set_yticks(np.arange(start=0, stop=state_frame['cases'].max() + 1))
    jhu_ax.bar(x=state_frame['state'], height=state_frame['cases'])
    jhu_ax.set_xlabel('State')
    jhu_ax.set_ylabel('Confirmed Cases')
    jhu_ax.set_title('Confirmed COVID-19 Cases in the United States by State')
    plt.savefig(ct.plot_path + 'state_sum.png')
    plt.show(block=False)
    plt.close()
    # Plot setup for city data
    plt.title('COVID-19 Cases by City')
    plt.gcf().set_size_inches(16, 16)
    plt.xticks(rotation=45, fontsize=8, fontweight='bold')
    plt.yticks(np.arange(start=0, stop=us_frame['cases'].max() + 1))
    plt.bar(x=us_frame['city'], height=us_frame['cases'])
    plt.xlabel('City')
    plt.ylabel('Confirmed Cases')
    plt.savefig(ct.plot_path + 'city_sum.png')
    plt.show(block=False)
    plt.close()
    # Plot setup for recovery data
    plt.title('COVID-19 Recoveries by State')
    plt.gcf().set_size_inches(15, 15)
    plt.xticks(rotation=45, fontsize=9, fontweight='bold')
    plt.yticks(np.arange(start=0, stop=us_frame['recoveries'].max() + 1))
    plt.bar(x=us_frame['state'], height=us_frame['recoveries'])
    plt.xlabel('State')
    plt.ylabel('Recoveries')
    plt.savefig(ct.plot_path + 'state_recov.png')
    plt.show(block=False)
    plt.close()

    ct.logger.info('Created plots!')
