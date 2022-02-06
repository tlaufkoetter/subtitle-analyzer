import os
import re

import pandas


class Card:
    def __init__(self, polish_word, german_word, polish_sentence, german_sentence, is_vocab):
        self.polish_word = re.sub(r'\n+', '', polish_word).strip()
        self.german_word = re.sub(r'\n+', '', german_word).strip()
        self.polish_sentence = re.sub(r'\n+', '', polish_sentence).strip()
        self.german_sentence = re.sub(r'\n+', '', german_sentence).strip()
        self.is_vocab = is_vocab


class CardExporter:
    def __init__(self, user_dir):
        self.__word_cards_file = os.path.join(user_dir, 'word_cards.csv')

    def get_cards(self):
        cards = {}
        if os.path.isfile(self.__word_cards_file):
            csv = pandas.read_csv(
                self.__word_cards_file, index_col=False, header=None)

            for line in csv.iterrows():
                word = line[1][0]
                print(word)
                if word:
                    cards[word.lower()] = True

        return cards

    def add_card(self, card: Card):
        data = pandas.DataFrame([[
            card.polish_word,
            card.german_word,
            card.polish_sentence,
            card.german_sentence,
            'true' if card.is_vocab else ''
        ]])

        with open(self.__word_cards_file, mode='a') as f:
            data.to_csv(f, header=False, index=False)
