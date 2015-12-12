from datetime import datetime, timedelta
import os

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

    def __init__(self, string, travel_time=None):
        parts = string.split(' ')
        self.day = self._parse_day(parts[0])

        parts = parts[1].split('-')
        self.start_time = datetime.strptime(parts[0], '%H:%M')
        self.end_time = datetime.strptime(parts[1], '%H:%M')

        if travel_time is None:
            travel_time = timedelta(minutes=0)

        self.travel_time = travel_time

    @staticmethod
    def _parse_day(string):
        for day, number in DAYS_OF_THE_WEEK.items():
            if day.startswith(string):
                return number
        raise ValueError('Could not understand day: {}'.format(string))

    def get_times(self):
        """Return the start and end time factoring in the travel time."""

        return self.start_time - self.travel_time, \
            self.end_time + self.travel_time

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

    travel_time : int
        The travel time in minutes.

    meeting_times : list[str]
        A list of parseable time periods.
    """

    def __init__(self, tla, arranged=False, travel_time=None,
                 meeting_times=None):
        if meeting_times is None:
            meeting_times = []

        self.tla = tla
        self.arranged = arranged
        self.travel_time = timedelta(minutes=travel_time or 0)
        self.meeting_times = [TimePeriod(s, self.travel_time)
                              for s in meeting_times]

        if not self.arranged:
            if not self.meeting_times:
                print('Warning: {} has no meeting times.'.format(self.tla))
            if not self.travel_time:
                print('Warning: {} has no travel time.'.format(self.tla))

    def __str__(self):
        return '{} ({})'.format(self.tla, self.travel_time)

    def find_suitable_mentors(self, all_mentors, tolerance=0):
        """Return a list of suitable mentors from all the mentors."""

        return [mentor
                for mentor in all_mentors
                if mentor.is_suitable_for(self, tolerance)]


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

        suitable_mentors = set(team.find_suitable_mentors(mentors))
        close_call_mentors = set(team.find_suitable_mentors(mentors, 10))

        close_call_mentors -= suitable_mentors

        if all(mentor.rookie for mentor in suitable_mentors):
            suitable_mentors = []

        if suitable_mentors and close_call_mentors:
            print('{}: {} ({})'
                  .format(team,
                          ', '.join(str(x) for x in suitable_mentors),
                          ', '.join(str(x) for x in close_call_mentors)))
        if close_call_mentors:
            print('{}: ({})'
                  .format(team,
                          ', '.join(str(x) for x in close_call_mentors)))
        else:
            print('{}: {}'
                  .format(team, ', '.join(str(x) for x in suitable_mentors)))


def main():
    """The main function of the scheduler."""

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('schedule')
    args = parser.parse_args()

    path = os.path.join('schedules', args.schedule) + '.yaml'
    with open(path) as file:
        data = yaml.safe_load(file)
        teams = [Team(tla, **team_data)
                 for tla, team_data in data['teams'].items()]
        mentors = [Mentor(name, **mentor_data)
                   for name, mentor_data in data['mentors'].items()]
        schedule(teams, mentors)


if __name__ == '__main__':
    main()
