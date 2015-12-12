from collections import defaultdict
from datetime import datetime, timedelta
import os
import pickle

from geopy.distance import vincenty
from geopy.geocoders import Nominatim
import yaml


DAYS_OF_THE_WEEK = {
    'Monday': 1,
    'Tuesday': 2,
    'Wednesday': 3,
    'Thursday': 4,
    'Friday': 5,
    'Saturday': 6,
    'Sunday': 7
}


class Geography:
    def __init__(self):
        self.geolocator = Nominatim()

        try:
            with open('.cache', 'rb') as file:
                self.cache = pickle.load(file)
        except FileNotFoundError:
            self.cache = defaultdict(dict)

    def save(self):
        with open('.cache', 'wb') as file:
            pickle.dump(self.cache, file)

    def geocode(self, query):
        if query in self.cache['GEOCODE']:
            return self.cache['GEOCODE'][query]

        location = self.geolocator.geocode(query)
        if location:
            self.cache['GEOCODE'][query] = location
            self.save()
        return location

    def distance(self, a, b):
        return vincenty(a, b).meters


class TimePeriod:
    """
    A time period with an optional travel time.

    The travel time is applied before the start time and after the end time.

    Parameters
    ----------

    string : str
        A parseable time period.

    travel_time : int
        The travel time in minutes.
    """

    def __init__(self, string):
        parts = string.split(' ')
        self.day = self._parse_day(parts[0])

        parts = parts[1].split('-')
        self.start_time = datetime.strptime(parts[0], '%H:%M')
        self.end_time = datetime.strptime(parts[1], '%H:%M')

    @staticmethod
    def _parse_day(string):
        for day, number in DAYS_OF_THE_WEEK.items():
            if day.startswith(string):
                return number
        raise ValueError('Could not understand day: {}'.format(string))

    def get_times(self):
        """Return the start and end time factoring in the travel time."""

        return self.start_time, self.end_time

    def fits_in(self, other_period, tolerance=0):
        """Check with this time period fits into the other time period."""

        if self.day != other_period.day:
            return False

        my_times_a, my_times_b = self.get_times()
        other_times_a, other_times_b = other_period.get_times()

        tolerance = timedelta(minutes=tolerance)
        my_times_a += tolerance
        my_times_b -= tolerance
        other_times_a -= tolerance
        other_times_b += tolerance

        return my_times_a >= other_times_a \
            and my_times_b <= other_times_b


class Team:
    """
    A team taking part in the competition.

    Parameters
    ----------

    tla : str
        The TLA of the team.

    meeting_times : list[str]
        A list of parseable time periods.
    """

    def __init__(self, tla, my_postcode, arranged=False, postcode=None,
                 meeting_times=None):
        if meeting_times is None:
            meeting_times = []

        self.tla = tla
        self.arranged = arranged
        self.postcode = postcode
        self.meeting_times = [TimePeriod(s) for s in meeting_times]

        if not self.arranged:
            if not self.meeting_times:
                print('Warning: {} has no meeting times.'.format(self.tla))

        geography = Geography()
        location = geography.geocode(self.postcode)

        if location:
            a = geography.geocode(my_postcode)
            b = (location.latitude, location.longitude)
            self.distance = geography.distance((a.latitude, a.longitude), b)
        else:
            self.distance = None
            print('Warning: {} has no distance.'.format(self.tla))

    def __str__(self):
        return '{} ({} km)'.format(self.tla, int(self.distance / 1000))

    def find_suitable_mentors(self, all_mentors):
        """Return a list of suitable mentors from all the mentors."""

        return [mentor
                for mentor in all_mentors
                if mentor.is_suitable_for(self)]


class Mentor:
    """
    A mentor who is able to do mentoring.

    Parameters
    ----------

    name : str
        The name of the mentor.

    rookie : bool
        Whether they are a new mentor.

    free_times : list[str]
        A list of parseable time periods.
    """

    def __init__(self, name, rookie=False, free_times=None):
        if free_times is None:
            free_times = []

        self.name = name
        self.rookie = rookie
        self.free_times = [TimePeriod(s) for s in free_times]

    def __str__(self):
        if self.rookie:
            return '{}*'.format(self.name)
        else:
            return self.name

    def is_suitable_for(self, team, tolerance=0):
        """Check whether a mentor is suitable for a team."""

        for free_time in self.free_times:
            for meeting_time in team.meeting_times:
                if meeting_time.fits_in(free_time, tolerance):
                    return True
        return False


def schedule(teams, mentors):
    """Schedule mentoring for some teams and some mentors."""

    for team in teams:
        if team.arranged:
            continue

        suitable_mentors = team.find_suitable_mentors(mentors)
        if all(mentor.rookie for mentor in suitable_mentors):
            suitable_mentors = []

        print('{}: {}'
              .format(team, ', '.join(str(x) for x in suitable_mentors)))


def main():
    """The main function of the scheduler."""

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('postcode')
    parser.add_argument('schedule')
    args = parser.parse_args()

    path = os.path.join('schedules', args.schedule)

    with open(os.path.join(path, 'teams.yaml')) as file:
        data = yaml.safe_load(file)
        teams = [Team(tla, args.postcode, **team_data)
                 for tla, team_data in data.items()]

    with open(os.path.join(path, 'mentors.yaml')) as file:
        data = yaml.safe_load(file)
        mentors = [Mentor(name, **mentor_data)
                   for name, mentor_data in data.items()]

    schedule(teams, mentors)


if __name__ == '__main__':
    main()
