import csv
import re
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


class WordInfo(object):
    def __init__(self, word):
        self.word = word
        self.filenames = []
        self.line_numbers = {}  # {filename: line_number_unsorted}
        self.issue_map = {}  # filename + str(line_number)

    def add(self, filename, line_number, issue):
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
            self.line_numbers[filename].append(line_number)

    def _add_or_merge_issue(self, issue_key, issue):
        if issue_key in self.issue_map:
            twin = self.issue_map[issue_key]
            for issue_type in issue.get_issue_types():
                twin.add_issue_type(issue_type)
        else:
            self.issue_map[issue_key] = issue

    def getIterator(self):
        return self._WordIterator(self.word, self.filenames, self.line_numbers)

    class _WordIterator(object):
        def __init__(self, word, filenames, line_numbers, issue_map):
            self.word = word
            self.filenames = sorted(filenames)
            self.line_numbers = sorted(line_numbers)
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
        assert issue_type in ('E', 'L', 'G', 'S')
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
        csvReader.next()  # Discard starting row
        return csvReader


class Translator(object):
    @staticmethod
    def getIssueLetter(issue_type):
        return issue_type[0]


def readCsvFile(csvFile):
    words = {}  # {word: WordInfo}
    for row in csvWrapper(csvFile).getReader():
        priority, file, line_num, issue_type, issue, code_line = row
        for word in re.split('\s+', code_line):
            issue = Issue(code_line, Translator.getIssueLetter(issue_type))
            if word in words:
                wordInfo = words[word]
            else:
                wordInfo = WordInfo(word)
                words[word] = wordInfo
            wordInfo.add(file, line_num, issue)
    return words


def printInfo(object):
    def __init__(self, wordInfo):
        self.wordInfo = wordInfo
        _print()

    def _setToLength(self, string, length):
        string += ' ' * max(0, length - len(string))
        return string[:-length]

    def _print(self):
        for issue_types, filename, line_num, line_content in self.wordInfo.getIterator():
            filename = self._setToLength(filename, FILENAME_LENGTH)
            print(issue_types, filename+":"+line_num, line_content)


def main():
    if len(sys.argv) != 2:
        usage()
        exit()
    csvFile = sys.argv[1]
    wordInfos = readCsvFile(csvFile)
    for wordInfo in sorted(wordInfos):
        printInfo(wordInfo)


def usage():
    print("python", sys.argv[0], "pathToCsvFile/csvFile.csv")

if __name__ == '__main__':
    main()
