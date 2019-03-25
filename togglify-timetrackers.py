#!/usr/bin/env python3
import csv
import datetime
import sys
import copy

"""
Browser tracking:
Domain,Path,Start timestamp,Finish timestamp,URL,Title
->
(
User,Email,Client,Project,Task,Description,Billable,Start date,Start time,End date,End time,Duration,Tags,Amount (USD)
->
User,Email,Client,Project,Task,Description,Start date,Start time,End date,End time
->
User,Email,Start date,End date,Client,Project,Task,Description,Start time,End time
)

(->User,->Email,->Start date,->End date),(Domain->|Path->)|Start timestamp->Start time, End timestamp->End time,(URL|Title)->(Client,Project,Task,Description),


ManicTime -> TimeYourWeb:
"Name","Start","End","Duration","Process"
Domain,Path,Start timestamp,Finish timestamp,URL,Title

Name->Domain, "" -> Path, Start -> Start timestamp, End->End Timestamp, Duration(delete), "" -> URL, Process -> Title

"""


# (->User,->Email,->Start date,->End date),(Domain->|Path->)|Start timestamp->Start time, End timestamp->End time,(URL|Title)->(Client,Project,Task,Description),


class TimeEntry(object):
    def __init__(self, domain, path, title, t_start, t_end):
        self.user = "Masnes"
        self.email = "masnes@lingoport.com"
        self.t_start = t_start
        self.t_end = t_end
        self.domain = domain
        self.client = None  # Client = type of work
        self.project = None  # Project = subcategory
        self.task = None  # Task = sub sub category
        self.description = "||".join([title, domain, path])
        self.subparts = []

    @property
    def start(self):
        return datetime.datetime.fromtimestamp(self.t_start)

    @property
    def end(self):
        return datetime.datetime.fromtimestamp(self.t_end)

    @property
    def duration(self):
        return self.end - self.start

    def __repr__(self):
        return "TimeEntry(user = {}, email = {}, start = {}, end = {}, t_start = {}, t_end = {}, " \
            "domain = {}, duration = {}, client = {}, project = {}, task = {}, description = {}" \
            ", subparts = {})""" \
            .format(self.user, self.email, self.start, self.end, self.t_start, self.t_end,
                    self.domain, self.duration, self.client, self.project, self.task,
                    self.description, self.subparts)

    def merge(self, time_entry):
        if len(time_entry.subparts) > 0:
            # can handle this via merging subparts if desired later
            # but if time entry is self, this would blow up
            raise AttributeError
        if time_entry == self:
            time_entry == copy.deepcopy(self)
        elif len(self.subparts) == 0:  # Make sure we have a sub-entry for first part
            self.merge(self)
        self.subparts.append(time_entry)
        self.t_end = time_entry.t_end
        self.description = "combined time entry"

    def get_longest(self, te_lambda):
        """o(n)"""
        if len(self.subparts) == 0:
            return te_lambda(self)
        description_times = {}
        for subpart in self.subparts:
            if te_lambda(subpart) in description_times:
                description_times[te_lambda(subpart)] += subpart.duration
            else:
                description_times[te_lambda(subpart)] = subpart.duration
        return sorted(description_times, key=description_times.get)[0]

    def to_csv_input(self):
        return [self.user, self.email, self.get_longest(lambda x: x.description), self.client,
                self.project, self.task,
                self.start.date().isoformat(), self.end.date().isoformat(),
                self.start.time().isoformat(), self.end.time().isoformat(),
                self.duration]


def consolidate_time_entries(time_entries):
    """merge time entries that are separated by less than max_idle minutes into
    blocks at least min_individual_block in size. Drop entries that are too
    small. For each entry, set descriptive variables to longest common one."""
    max_idle = datetime.timedelta(minutes=15)
    min_individual_block = datetime.timedelta(minutes=8)

    merged = []
    time_group = None
    for time_entry in time_entries:
        if time_group is None:
            time_group = time_entry
        gap_time = (datetime.timedelta(seconds=0) if time_entry == time_group
                    else time_entry.start - time_group.end)
        if gap_time < max_idle:
            if time_entry.duration < min_individual_block:  # Too small. rope into previous
                time_group.merge(time_entry)
            elif (time_entry.description == time_group.get_longest(lambda x: x.description)
                  or time_entry.domain   == time_group.get_longest(lambda x: x.domain)):
                # Large enough, but similar to previous
                time_group.merge(time_entry)
            else:
                # Large enough to trigger new section, and not similar to previous
                merged.append(time_group)
                time_group = time_entry
        else:
            merged.append(time_group)
            time_group = time_entry
    if time_group is not None:
        merged.append(time_group)
    if not merged:
        raise AttributeError(str(len(time_entries)) + " -> 0" + "{}".format(time_group))
    return [time_group for time_group in merged if time_group.duration > min_individual_block]


def gap_fill_time_entries(time_entries):
    """Add time entries for blank spaces that reside in the middle of a sorted
    time entry iterable where the blank spaces fit within a minimum and maximum
    allowed time."""
    max_gap = datetime.timedelta(hours=4)
    min_entry_size = datetime.timedelta(minutes=8)
    gap_filled_time_entries = []
    prev_entry = None
    for entry in time_entries:
        if prev_entry:
            entry_delta = entry.start - prev_entry.end
            if max_gap >= entry_delta and entry_delta >= min_entry_size:
                gap_entry = TimeEntry("Not Logged", "Unknown Path", "Unknown Focus",
                                      prev_entry.t_end + 1, entry.t_start - 1)
                gap_filled_time_entries.append(gap_entry)
            elif entry_delta < min_entry_size:
                prev_entry.t_end = entry.t_start - 1
        gap_filled_time_entries.append(entry)
        prev_entry = entry
    return gap_filled_time_entries


def get_next(generator):
    """Get next item in generator manually. Python2 and 3 compatible."""
    try:
        return generator.__next__()
    except AttributeError:
        return generator.next()


def manictime_to_timestamp(time):
    """Convert from "3/4/2019 11:33:52 AM" to unix timestamp"""
    dt = datetime.datetime.strptime(time, "%m/%d/%Y %I:%M:%S %p")
    return dt.timestamp()


def transform_file(somefile):
    manictime = False
    timeyourweb = False
    if "Flow" in somefile:
        outfile = somefile.replace("Flow", "Toggle")
        timeyourweb = True
    if "ManicTime" in somefile:
        outfile = somefile.replace("ManicTime", "Toggle")
        manictime = True
    if not manictime and not timeyourweb:
        print("refusing to transform file: ", somefile, ", does not match expected name.")
        return
    with open(somefile, "r") as timeyourweb_output:
        reader = csv.reader(timeyourweb_output)
        time_entries = [
            ["User", "Email", "Description", "Client", "Project", "Task",
             "Start date", "End date", "Start time", "End time", "Duration"]
        ]
        try:
            get_next(reader)  # Dump column names
            while True:
                # TimeYourWeb: Domain,Path,Start timestamp,Finish timestamp,URL,Title
                # ManicTime: Name,Start,End,Duration,Process
                next_ = get_next(reader)
                if len(next_) == 6 and timeyourweb:
                    domain, path, t_start, t_end, _, title = next_
                    t_start = int(t_start) / 1000  # Timestamps are too big by factor of 1000
                    t_end = int(t_end) / 1000  # Timestamps are too big b factor of 1000
                elif len(next_) == 5 and manictime:
                    name, start, end, duration, process = next_
                    domain = name
                    path = ""
                    t_start = manictime_to_timestamp(start)
                    t_end = manictime_to_timestamp(end)
                    title = process
                else:
                    print(somefile, ": ")
                    print("Aborting due to extra input!")
                    print(next_)
                    exit(1)
                timeEntry = TimeEntry(domain, path, title, t_start, t_end)
                time_entries.append(timeEntry)
        except StopIteration:
            pass

    time_entries_consolidated = consolidate_time_entries(time_entries[1:])
    time_entries_consolidated_and_gap_filled = gap_fill_time_entries(time_entries_consolidated)

    with open(outfile, "w") as toggle_outfile:
        writer = csv.writer(toggle_outfile)
        # [user, email, description, client, project, task, d_start, d_end, t_start, t_end, duration]
        writer.writerow(["User", "Email", "Description", "Client", "Project", "Task",
                         "Start date", "End date", "Start time", "End time", "Duration"])
        for entry in time_entries_consolidated_and_gap_filled:
            writer.writerow(entry.to_csv_input())


def main():
    for somefile in sys.argv[1:]:
        transform_file(somefile)


if __name__ == '__main__':
    main()
