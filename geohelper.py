# NOTICE: This class is now deprecated as JHU no longer reports city level data


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

    def __init__(self, state_name: str, state_cases: int, state_deaths: int, state_recoveries: int):
        self.name = state_name
        self.cases = int(state_cases)
        self.deaths = int(state_deaths)
        self.recoveries = int(state_recoveries)

    def get_name(self):
        """Returns the name of the state"""

        return self.name

    def get_cases(self) -> int:
        """Gets the total number of cases from each city in the state"""

        return self.cases

    def get_deaths(self) -> int:
        """Gets the total number of deaths from each city in the state"""

        return self.deaths

    def get_recoveries(self) -> int:
        """Gets the total number of recoveries from each city in the state"""

        return self.recoveries
