import sys
import os.path


class IO:
    def __init__(self, filename):
        self.console = sys.stdout
        self.file = open(filename, 'a')

    def write(self, message):
        self.console.write(message)
        self.file.write(message)

    def flush(self):
        pass

    @staticmethod
    def conditional_print(message, condition):
        if condition:
            print(message)

    @staticmethod
    def read_keys_from_file(filename):
        if not os.path.isfile(filename):
            print(f'Provided file {filename} does not exist. Exiting...')
            return
        else:
            print(f'Starting validation on keys in {filename}')
        try:
            with open(filename, 'r') as file:
                keys_in_file = set()
                for line in file:
                    current_line = line.strip()
                    if not current_line:
                        continue
                    keys_in_file.add(current_line.split()[0].split(",")[0])
                return keys_in_file
        except Exception as e:
            print(f'Unable to read keys from {filename}')
            return
