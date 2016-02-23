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


class Word(object):
    def __init__(self, word):
        self.word = word
        self.filenames = []
        self.line_numbers = {}  # {filename: line_number_unsorted}
        self.issue_map = {}  # filename + str(line_number)

    def add(self, filename, line_number, issue):
        if filename not in self.filenames:
            self.filenames.append(filename)
        if filename not in self.line_numbers:
            self.line_numbers[filename] = [line_number]
        else:
            self.line_numbers[filename].append(line_number)
        issue_key = filename + str(line_number)
        assert issue_key not in self.issue_map
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
        self.issue_types = set(issue_type)

    def add_issue_type(self, issue_type):
        assert issue_type in ('E', 'L', 'G', 'S')
        self.issue_types.add(issue_type)

    def get_issue_types(self):
        ret = ''
        for issue_type in ('E', 'L', 'G', 'S'):
            ret += issue_type if issue_type in self.issue_types else ' '
        return ret


def main():
    pass

if __name__ == '__main__':
    main()
