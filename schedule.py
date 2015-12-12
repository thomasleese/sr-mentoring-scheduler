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
    def __init__(self, string, travel_time=None):
        parts = string.split(' ')
        self.day = self.parse_day(parts[0])

        parts = parts[1].split('-')
        self.start_time = datetime.strptime(parts[0], '%H:%M')
        self.end_time = datetime.strptime(parts[1], '%H:%M')

        if travel_time is not None:
            self.travel_time = timedelta(minutes=travel_time)
        else:
            self.travel_time = 0

    @staticmethod
    def parse_day(string):
        for day, number in DAYS_OF_THE_WEEK.items():
            if day.startswith(string):
                return number
        raise ValueError('Could not understand day: {}'.format(string))

    def get_times(self):
        return self.start_time - self.travel_time, \
            self.end_time + self.travel_time

    def fits_in(self, other_period, include_travel_time=False):
        if self.day != other_period.day:
            return False

        my_times = self.get_times()
        other_times = self.get_times()

        return my_times[0] >= other_times[0] \
            and my_times[1] <= other_times[1]


class Team:
    def __init__(self, tla, travel_time=0, meeting_times=None):
        if meeting_times is None:
            meeting_times = []

        self.tla = tla
        self.travel_time = travel_time
        self.meeting_times = [TimePeriod(s, travel_time)
                              for s in meeting_times]

        if not self.meeting_times:
            print('Warning: {} has no meeting times.'.format(self.tla))
        if not self.travel_time:
            print('Warning: {} has no travel time.'.format(self.tla))

    def find_suitable_mentors(self, all_mentors):
        return [mentor
                for mentor in all_mentors
                if mentor.is_suitable_for(self)]


class Mentor:
    def __init__(self, name, free_times=None):
        if free_times is None:
            free_times = []

        self.name = name
        self.free_times = [TimePeriod(s) for s in free_times]

    def is_suitable_for(self, team):
        for free_time in self.free_times:
            for meeting_time in team.meeting_times:
                if meeting_time.fits_in(free_time):
                    return True


def schedule(teams, mentors):
    for team in teams:
        suitable_mentors = team.find_suitable_mentors(mentors)
        print('{}: {}'
              .format(team.tla,
                      ', '.join(mentor.name for mentor in suitable_mentors)))


def main():
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
