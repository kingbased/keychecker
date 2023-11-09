import sys


class Logger:
    def __init__(self, filename):
        self.console = sys.stdout
        self.file = open(filename, 'a')

    def write(self, message):
        self.console.write(message)
        self.file.write(message)

    def flush(self):
        pass
