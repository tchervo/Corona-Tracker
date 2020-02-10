import numpy as np

class City:
    """
    Contains data at the city level
    """

    def __init__(self, city_name: str, case_info: list):
        self.name = city_name
        self.data = case_info

    def get_name(self) -> str:
        """Returns the name of the city"""

        return self.name

    def get_cases(self) -> int:
        """Returns the number of confirmed cases for this city"""

        return self.data[0]

    def get_deaths(self) -> int:
        """Returns the number of confirmed deaths for this city"""

        return self.data[1]

    def get_recoveries(self) -> int:
        """Returns the number of confirmed recoveries for this city"""

        return self.data[2]


class State:
    """
    A State object to contain cities and state level data
    """

    def __init__(self, state_name: str, state_cities: list):
        self.name = state_name
        self.cities = state_cities

    def get_name(self):
        """Returns the name of the state"""

        return self.name

    def get_cities(self):
        """Returns a list of city objects within a state"""

        return self.cities

    def get_city_names(self):
        """Returns a list of the city names"""

        return [city.get_name() for city in self.cities]

    def get_cases(self) -> int:
        """Gets the total number of cases from each city in the state"""

        all_cases = [city.get_cases() for city in self.cities]

        return np.sum(all_cases)

    def get_deaths(self) -> int:
        """Gets the total number of deaths from each city in the state"""

        all_deaths = [city.get_deaths() for city in self.cities]

        return np.sum(all_deaths)

    def get_recoveries(self) -> int:
        """Gets the total number of recoveries from each city in the state"""

        all_recovs = [city.get_recoveries() for city in self.cities]

        return np.sum(all_recovs)


    # def get_case_difference(self, comparison):
    #     """
    #     Calculates the difference in case data between this state and a comparison, and returns a list of
    #     differences
    #     :param comparison: The state to compare to. Should be a state object
    #     :return: A list of differences in case information
    #     """
    #
    #
