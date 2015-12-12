import os

import icalendar
import yaml


WEEK_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def busy_times_to_free_times(busy_times):
    pass


def main():
    """The main function of the calendar importer."""

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('ical')
    parser.add_argument('mentor')
    parser.add_argument('schedule')
    args = parser.parse_args()

    with open(args.ical) as file:
        calendar = icalendar.Calendar.from_ical(file.read())

    path = os.path.join('schedules', args.schedule)
    with open(os.path.join(path, 'mentors.yaml')) as file:
        mentor_data = yaml.safe_load(file)

    mentor_data[args.mentor]['free_times'] = []
    mentor_data[args.mentor]['busy_times'] = []
    for thing in calendar.walk('VEVENT'):
        day = WEEK_DAYS[thing['DTSTART'].dt.weekday()]
        start = thing['DTSTART'].dt.strftime('%H:%M')
        end = thing['DTEND'].dt.strftime('%H:%M')
        s = '{} {}-{}'.format(day, start, end)
        mentor_data[args.mentor]['busy_times'].append(s)

    with open(os.path.join(path, 'mentors.yaml'), 'w') as file:
        file.write(yaml.dump(mentor_data, default_flow_style=False))


if __name__ == '__main__':
    main()
