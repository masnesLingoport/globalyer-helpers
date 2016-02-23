import csv
import re
import string
import sys
"""
Print out all lines containing a similar word.
Ignore duplicates.
Order: By word, then file, then line number

[("line number", hash)]  # To allow retrieval based on line number
                        v should be ordered based on line number
{hash: (word, [(issue, line_number)])}
set("hashes of combined issue details")  # to avoid logging duplicates

Create hashes by hashing combination of all filenames in a list.

Output: ELGS Truncated filename:line#, issue
"""

FILENAME_LENGTH = 30
PUNCTUATION_SET = set(string.punctuation)
PUNCTUATION_SET.remove('_')

MIN_SIMILAR_DEFAULT = 2


class WordInfo(object):
    def __init__(self, word):
        self.word = word
        self.filenames = []
        self.line_numbers = {}  # {filename: line_number_unsorted}
        self.issue_map = {}  # filename + str(line_number)

    def __len__(self):
        return len(self.issue_map)

    def add(self, filename, line_number, issue):
        line_number = int(line_number)
        self._add_filename(filename)
        self._add_line_number(filename, line_number)
        issue_key = self._issue_key(filename, line_number)
        self._add_or_merge_issue(issue_key, issue)

    def _issue_key(self, filename, line_number):
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

    def _add_or_merge_issue(self, issue_key, issue):
        if issue_key in self.issue_map:
            if self.issue_map[issue_key].get_issue_types() != issue.get_issue_types():
                print(self.issue_map[issue_key].get_issue_types())
                print(issue.get_issue_types())
                exit()
            twin = self.issue_map[issue_key]
            for issue_type in issue.get_issue_types().replace(' ', ''):
                twin.add_issue_type(issue_type)
        else:
            self.issue_map[issue_key] = issue

    def getIterator(self):
        return self._WordIterator(self.word, self.filenames, self.line_numbers, self.issue_map)

    class _WordIterator(object):
        def __init__(self, word, filenames, line_numbers, issue_map):
            self.word = word
            self.filenames = sorted(filenames)
            self.line_numbers = line_numbers
            self.issue_map = issue_map

        def __iter__(self):
            return self

        def __next__(self):
            for filename in self.filenames:
                for line_num in self.line_numbers[filename]:
                    issue = self.issue_map[filename + str(line_num)]
                    issue_types = issue.get_issue_types()
                    line_content = issue.line_content
                    yield issue_types, filename, line_num, line_content
            raise StopIteration


class Issue(object):
    def __init__(self, line_content, issue_type):
        self.line_content = line_content
        self._issue_types = set(issue_type)

    def add_issue_type(self, issue_type):
        assert issue_type in ('E', 'L', 'G', 'S'), issue_type
        self._issue_types.add(issue_type)

    def get_issue_types(self):
        ret = ''
        for issue_type in ('E', 'L', 'G', 'S'):
            ret += issue_type if issue_type in self._issue_types else ' '
        return ret


class csvWrapper(object):
    def __init__(self, csvFile):
        self.csvFile = csvFile

    def getReader(self):
        csvReader = csv.reader(self.csvFile)
        csvReader.__next__()  # Discard starting row
        return csvReader


class Translator(object):
    @staticmethod
    def getIssueLetter(issue_type):
        return issue_type[0]


def remove_punctuation(word):
    return ''.join(ch for ch in word if ch not in PUNCTUATION_SET)


def readCsvFile(csvFile):
    words = {}  # {word: WordInfo}
    with open(csvFile) as f:
        reader = csv.reader(f)
        reader.__next__()  # Discard starting row
        for priority, file_, line_num, issue_type, issue, code_line in reader:
            # if re.match("[^_\w\"'\(\)\[\]\{\}]+$", word):  # Only Punctuation, no brackets/'"
            for word in re.split("[^\w_]", code_line):
                word = remove_punctuation(word)
                if len(word) < 2:
                    continue

                issue = Issue(code_line, Translator.getIssueLetter(issue_type))
                wordInfo = words[word] if word in words else WordInfo(word)
                words[word] = wordInfo
                wordInfo.add(file_, line_num, issue)
    return words


def setToLength(string, length):
    string += ' ' * max(0, length - len(string))
    return string[-length:]


def print_(wordInfo, min_similar_issues):
    if len(wordInfo) < min_similar_issues:
        return
    it = wordInfo.getIterator()
    it = it.__next__()
    print()
    print(wordInfo.word + ":")
    for issue_types, filename, line_num, line_content in it:
        filename = setToLength(filename, FILENAME_LENGTH)
        print(issue_types, filename+":"+str(line_num), line_content)


def main():
    if 2 > len(sys.argv) or len(sys.argv) > 3:
        usage()
        exit()
    csvFile = sys.argv[1]
    min_similar_issues = int(sys.argv[2] if len(sys.argv) == 3 else MIN_SIMILAR_DEFAULT)
    wordInfos = readCsvFile(csvFile)
    for word in sorted(wordInfos, key=lambda s: s.lower()):
        print_(wordInfos[word], min_similar_issues)


def usage():
    print("Usage:")
    print("python", sys.argv[0], "pathToCsvFile/csvFile.csv", "[min_similar]")

if __name__ == '__main__':
    main()
