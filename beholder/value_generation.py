

class FileLoader:
    def __init__(self, filepath):
        self._filepath = filepath

    def get_value_sets(self):
        with open(self._filepath, encoding='latin-1') as file:
            count = 0

            line = file.readline()
            while line:
                count += 1
                yield line.strip()
                line = file.readline()

        # count = 0
        # for line in lines:
        #     result.append(('auction', line))
        #     count += 1
        #     if count % 2 == 0:
        #         result.append(('weiner', 'peter'))
    

if __name__ == '__main__':
    loader = FileLoader('bob.txt')
    for valset in loader.get_value_sets():
        print(valset)

class TokenRange:

    def get_value_sets(self):
        for i in range(2000):
            yield str(i).zfill(4)
