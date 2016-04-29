"""
Print out code lines for all issues who's code lines contain a similar word.

Order: By word, then file, then line number

Output:
'
word:
ELGS (Truncated)filename:line# issue code line
'
Flags ELGS indicate what issue types are relevant to the code line.
E: Embedded Strings
L: Locale Sensitive Methods
G: General Patterns
S: Static File References
"""
from __future__ import print_function

import csv
import re
import string
import sys


FILENAME_LENGTH = 30
PUNCTUATION_SET = set(string.punctuation)
PUNCTUATION_SET.remove('_')

MIN_SIMILAR_DEFAULT = 2
DEFAULT_DESIRED_ISSUES = "ELGS"

IGNORED_WORDS = set(
    ["add", "and", "the", "if", "else", "in", "for", "self", "this", "true", "false", "function",
     "is", "not", "null", "of",
     ]
)


class WordInfo(object):
    """ Store all data relevant to a single word.
    Filenames containing word.
    Line numbers relevant to each file name.
    Issues relevant to each File and Line Number
    """
    def __init__(self, word):
        self.word = word
        self.filenames = []
        self.line_numbers = {}  # {filename: [line_numbers_unsorted]}
        self.line_map = {}  # {filename+str(line_number): line}

    def __len__(self):
        return len(self.line_map)

    def add(self, filename, line_number, line):
        """ Add an issue that contains this word """
        line_number = int(line_number)
        self._add_filename(filename)
        self._add_line_number(filename, line_number)
        line_key = self._line_key(filename, line_number)
        self._add_or_merge_line(line_key, line)

    @staticmethod
    def _line_key(filename, line_number):
        return filename + str(line_number)

    def _add_filename(self, filename):
        if filename not in self.filenames:
            self.filenames.append(filename)

    def _add_line_number(self, filename, line_number):
        if filename not in self.line_numbers:
            self.line_numbers[filename] = [line_number]
        else:
            line_number_list = self.line_numbers[filename]
            if len(line_number_list) == 0 or line_number_list[-1] != line_number:
                line_number_list.append(line_number)

    def _add_or_merge_line(self, line_key, line):
        if line_key not in self.line_map:
            self.line_map[line_key] = line
            return
        current_issues = self.line_map[line_key].get_issue_set()
        new_issues = line.get_issue_set()
        difference = new_issues.difference(current_issues)
        if len(difference) > 0:
            for issue_type in difference:
                self.line_map[line_key].add_issue_type(issue_type)
            if len(difference) > 1:
                print("Hmm. More than one difference in this issue")
                print(difference)
                exit()

    def line_info_in_sorted_order(self):
        """ Generator yielding all info pertaining to each line.
        Results ordered by filename, then by line number.
        """
        for filename in sorted(self.filenames):
            for line_num in self.line_numbers[filename]:  # Already sorted
                line = self.line_map[filename + str(line_num)]
                issue_types = line.get_issue_types()
                line_content = line.line_content
                yield issue_types, filename, line_num, line_content
        raise StopIteration


class Line(object):
    """ Line content, and all issues associated with it """
    def __init__(self, line_content, issue_type):
        self.line_content = line_content
        self._issue_types = set(issue_type)

    def add_issue_type(self, issue_type):
        """Note that this line has an issue of type issue_type,
        must be E, L, G, or S
        """
        assert issue_type in ('E', 'L', 'G', 'S'), issue_type
        self._issue_types.add(issue_type)

    def get_issue_set(self):
        """Get set of single letter representations of issue types associated
        with this line
        """
        return self._issue_types

    def get_issue_types(self):
        """Get 4 character string of issue types associated with this line.
        Characters will be ' ' if that character's issue is not associated with
        this line.

        Example:
            "EL S"
        (No general patterns on the line)
        """
        ret = ''
        for issue_type in ('E', 'L', 'G', 'S'):
            ret += issue_type if issue_type in self._issue_types else ' '
        return ret


def get_issue_letter(full_issue_type_string):
    """Takes an issue type string like "Embedded Strings" and returns the
    associated issue letter (would be 'E')
    """
    return full_issue_type_string[0]


def remove_punctuation(word):
    """Remove punctuation symbols from word. Does not remove underscores"""
    return ''.join(ch for ch in word if ch not in PUNCTUATION_SET)


def read_csv_file(scan_detailed_csv_file):
    """ Build a list of Words and their associated fields from a scan_detailed_csv file"""
    words = {}  # {word: WordInfo}
    with open(scan_detailed_csv_file) as scan_detailed_csv_file:
        # state = 0
        reader = csv.reader(scan_detailed_csv_file)
        try:
            reader.__next__()
        except AttributeError:
            reader.next()  # Discard starting row
        #   priority, file, line_num, issue_type, issue, code_line
        for _, file_, line_num, issue_type, _, code_line in reader:
            # if re.match("[^_\w\"'\(\)\[\]\{\}]+$", word):  # Only Punctuation, no brackets/'"
            for word in re.split(r"[^\w_]", code_line):
                word = remove_punctuation(word)
                if len(word) < 2 or word in IGNORED_WORDS or re.match(r"\d+$", word):
                    continue

                line = Line(code_line, get_issue_letter(issue_type))
                word_info = words[word] if word in words else WordInfo(word)
                words[word] = word_info
                word_info.add(file_, line_num, line)
    return words


def set_to_length(string_, length):
    """Force strength to be len length by either truncating it from the front,
    or appending spaces to it.
    """
    string_ += ' ' * max(0, length - len(string_))
    return string_[-length:]


def print_info_for_word(word_info, min_similar_issues, desired_issue_types):
    """For each line containing this word (in the relevant WordInfo) print the
    following:
    issue_types filename(set_to_length FILENAME_LENGTH):line# code_line
    E.g.
    EL S truncatedPath/someFile:229 example.append("An Example, path/file.html")
    """
    def desired_issue_found(issue_types, desired_issue_types):
        """Determine if any of the desired issue types are part of the actual
        issue types
        """
        for issue in desired_issue_types:
            if issue in issue_types:
                return True
        return False

    if len(word_info) < min_similar_issues:
        return
    print()
    print(word_info.word + ":")
    for (issue_types, filename, line_num, line_content) in \
            word_info.line_info_in_sorted_order():
        if not desired_issue_found(issue_types, desired_issue_types):
            continue
        filename = set_to_length(filename, FILENAME_LENGTH)
        print(issue_types, filename+":"+str(line_num), line_content)


def main():
    """Print usage message if wrong number of args.
    Otherwise, run program and send output to stdout
    """
    if not 3 <= len(sys.argv) <= 4:
        usage()
        exit()
    csv_file = sys.argv[1]
    min_similar_lines = int(sys.argv[2] if len(sys.argv) >= 3 else MIN_SIMILAR_DEFAULT)
    desired_issue_types = sys.argv[3] if len(sys.argv) >= 4 else DEFAULT_DESIRED_ISSUES
    word_infos = read_csv_file(csv_file)
    print("Words ")
    for word in sorted(word_infos, key=lambda s: s.lower()):
        word_info = word_infos[word]
        if len(word_info) > min_similar_lines:
            print(word)
    print()
    for word in sorted(word_infos, key=lambda s: s.lower()):
        print_info_for_word(word_infos[word], min_similar_lines, desired_issue_types)


def usage():
    """Print a usage message"""
    print("Usage:")
    print("python", sys.argv[0], "pathToCsvFile/csvFile.csv", "[min_similar]",
          "[desired_issue_types]")

if __name__ == '__main__':
    main()
