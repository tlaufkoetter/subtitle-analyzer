import os


class KnowledgeBase:
    def __init__(self, data_dir):
        self.__known_file = os.path.join(data_dir, 'known.csv')
        self.__black_list_file = os.path.join(data_dir, 'black_list.csv')

    def __load_words(self, file_name):
        if not os.path.isfile(file_name):
            return {}

        with open(file_name, 'r') as known_file:
            return {l.strip(): True for l in known_file.readlines()}

    def __update_words(self, words, file_name):
        known = self.__load_words(file_name)

        with open(file_name, 'w+') as known_file:
            for word in words:
                known[word] = True

            known_file.writelines([k + '\n' for k in known.keys()])

    def update_known_words(self, known_words):
        self.__update_words(known_words, self.__known_file)

    def update_black_list(self, black_list):
        self.__update_words(black_list, self.__black_list_file)

    def get_known_words(self):
        return self.__load_words(self.__known_file)

    def get_black_list(self):
        return self.__load_words(self.__black_list_file)
