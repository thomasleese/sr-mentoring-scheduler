from collections import defaultdict
from datetime import datetime, timedelta
import os
import pickle

from geopy.distance import vincenty
from geopy.geocoders import Nominatim
import jinja2
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

MAX_SPEED = 50  # km/h


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
        self.day, self.day_string = self._parse_day(parts[0])

        parts = parts[1].split('-')
        self.start_time = datetime.strptime(parts[0], '%H:%M')
        self.end_time = datetime.strptime(parts[1], '%H:%M')

    def __str__(self):
        return '{} {}-{}'.format(self.day_string[:3],
                                 self.start_time.strftime('%H:%M'),
                                 self.end_time.strftime('%H:%M'))

    @staticmethod
    def _parse_day(string):
        for day, number in DAYS_OF_THE_WEEK.items():
            if day.startswith(string):
                return number, day
        raise ValueError('Could not understand day: {}'.format(string))

    def get_times(self):
        """Return the start and end time factoring in the travel time."""

        return self.start_time, self.end_time

    def fits_in(self, other_period):
        """Check with this time period fits into the other time period."""

        if self.day != other_period.day:
            return False

        my_times_a, my_times_b = self.get_times()
        other_times_a, other_times_b = other_period.get_times()

        return my_times_a > other_times_a \
            and my_times_b < other_times_b


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
            self.distance_km = self.distance / 1000
        else:
            self.distance = None
            self.distance_km = None
            print('Warning: {} has no distance.'.format(self.tla))

    def __str__(self):
        return '{} ({} km)'.format(self.tla, int(self.distance / 1000))

    def find_suitable_mentors(self, all_mentors):
        """Return a list of suitable mentors from all the mentors."""

        if self.arranged:
            return []

        for mentor in all_mentors:
            suitable_mentor = mentor.is_suitable_for(self)
            if suitable_mentor:
                yield suitable_mentor


class SuitableMentor:
    def __init__(self, mentor, team, meeting_time, free_time):
        self.mentor = mentor
        self.team = team

        self.meeting_time = meeting_time

        meeting_time_a, meeting_time_b = meeting_time.get_times()
        free_time_a, free_time_b = free_time.get_times()

        self.journey_there = meeting_time_a - free_time_a
        self.journey_back = free_time_b - meeting_time_b

        self.min_journey_time = min(self.journey_there, self.journey_back)
        self.max_journey_time = max(self.journey_there, self.journey_back)

        self.min_journey_speed = team.distance / \
            self.min_journey_time.total_seconds()

        self.journey_there_speed = team.distance_km / \
            (self.journey_there.total_seconds() / 60 / 60)
        self.journey_back_speed = team.distance_km / \
            (self.journey_back.total_seconds() / 60 / 60)

        self.min_journey_speed = min(self.journey_there_speed,
                                     self.journey_back_speed)
        self.max_journey_speed = max(self.journey_there_speed,
                                     self.journey_back_speed)


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

    def is_suitable_for(self, team):
        """Check whether a mentor is suitable for a team."""

        for free_time in self.free_times:
            for meeting_time in team.meeting_times:
                if meeting_time.fits_in(free_time):
                    suitable_mentor = SuitableMentor(self, team, meeting_time,
                                                     free_time)
                    if suitable_mentor.max_journey_speed < MAX_SPEED:
                        return suitable_mentor
        return None

    def find_suitable_teams(self, all_teams):
        """Return a list of suitable teams from all the mentors."""

        for team in all_teams:
            if team.arranged:
                continue

            suitable_mentor = self.is_suitable_for(team)
            if suitable_mentor:
                yield suitable_mentor


def schedule(teams, mentors):
    """Schedule mentoring for some teams and some mentors."""

    with open('template.html') as file:
        template = jinja2.Template(file.read())

    output = template.render(teams=teams, mentors=mentors)
    with open('output.html', 'w') as file:
        file.write(output)


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
