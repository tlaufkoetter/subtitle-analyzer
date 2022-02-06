
import os
from typing import Generator
import lemmagen3
import re

from knowledge_base import KnowledgeBase

lt_pl = lemmagen3.Lemmatizer('pl')


class SentenceContext:
    def __init__(self, sentence, start, end):
        self.sentence = sentence
        self.start = start
        self.end = end
        self.translation = None

    def __str__(self) -> str:
        return self.sentence


class WordOccurance:
    def __init__(self, word):
        self.count = 0
        self.word = word
        self.forms = {}
        self.sentence_contexts = []

    def add(self, form, sentence_context: SentenceContext):
        self.count += 1
        if self.forms.get(form) is None:
            self.forms[form] = 0

        self.forms[form] += 1

        self.sentence_contexts.append(sentence_context)

    def __calc(self, known_words, context):
        wordsss = [(1 if known_words.get(lt_pl.lemmatize(word.lower())) else 0) for word in re.split(
            r'\W+', str(context))]
        word_count = len(wordsss)
        known_words_count = sum(wordsss)
        unknown_words_count = word_count - known_words_count
        return unknown_words_count, word_count/float(known_words_count) if known_words_count > 0 else 1.0

    def get_context(self, known_words):
        di = ((context, self.__calc(known_words, context))
              for context in self.sentence_contexts)
        return sorted(di, key=lambda c: c[1])


class WordStats:
    def __init__(self, word_occurance: WordOccurance, percentile):
        self.word_occurance = word_occurance
        self.percentile = percentile


class WordCounter:
    class __Context:
        def __init__(self):
            self.sentences = []
            self.__reset_block()

        def __reset_block(self):
            self.has_started = False
            self.start = (0, 0, 0, 0)
            self.end = (0, 0, 0, 0)
            self.this_sentence = None

        def finish_block(self, get_sentences):
            if self.this_sentence:
                self.sentences.extend(get_sentences(
                    self.this_sentence, self.start, self.end))

            self.__reset_block()

        def set_timestamp(self, line):
            m = re.match(
                r'^(\d\d):(\d\d):(\d\d).(\d\d\d) --> (\d\d):(\d\d):(\d\d).(\d\d\d)', line)
            if m:
                self.start = (int(m.group(1)), int(m.group(2)),
                              int(m.group(3)), int(m.group(4)))
                self.end = (int(m.group(5)), int(m.group(6)),
                            int(m.group(7)), int(m.group(8)))

        def parse_line(self, line):
            text_line = re.sub(r'<[^>]+>', '', line)
            text_line = re.sub(r'\[[^\]]+\]', '', text_line)
            text_line = re.sub(r'- ?', '', text_line)
            text_line = text_line.strip()
            if not self.this_sentence:
                self.this_sentence = text_line
            else:
                self.this_sentence += ' ' + text_line

        def start_block(self):
            self.has_started = True

    def __init__(self, knowledge_base: KnowledgeBase, subtitles_dir):
        self.subtitles_dir = subtitles_dir
        self.knowledge_base = knowledge_base

    def __parse_sentences(self, translated_lines, get_sentences):
        context = self.__Context()
        for line in translated_lines:
            if re.match(r'^\s*$', line):
                context.finish_block(get_sentences)
            elif context.has_started and re.match(r'^\d\d:\d\d:\d\d', line):
                context.set_timestamp(line)
            elif context.has_started:
                context.parse_line(line)
            elif re.match(r'^\d+$', line):
                context.start_block()

        return context.sentences

    def __get_translated_sentences(self, translated_lines):
        return self.__parse_sentences(translated_lines, lambda this_sentence, start, end: [
                                     (this_sentence, start, end)])

    def __process_lines(self, lines, translated_lines):
        translated_sentences = self.__get_translated_sentences(
            translated_lines)
        return self.__parse_sentences(lines, lambda this_sentence, start, end: self.__process_single_subtitle(this_sentence, start, end, translated_sentences))

    def __is_between(self, lower_bound, value, upper_bound):
        return lower_bound <= value and value <= upper_bound

    def __find_translation(self, translated_sentences, sentence_context):
        ft = None
        lt = None
        found = True
        for i, trans in enumerate(translated_sentences):
            if self.__is_between(trans[1], sentence_context.start, trans[2]) or self.__is_between(sentence_context.start, trans[1], sentence_context.end):
                ft = i, trans[0]
            if self.__is_between(trans[1], sentence_context.end, trans[2]) or self.__is_between(sentence_context.start, trans[2], sentence_context.end):
                lt = i, trans[0]

            if ft is not None:
                break
        else:
            found = False

        if not found:
            return None

        if ft == lt or lt is None:
            return ft[1]
        else:
            return ft[1] + ' ' + lt[1]

    def __process_single_subtitle(self, this_sentence, start, end, translated_sentences):
        if not this_sentence:
            return

        sentence_context = SentenceContext(
            this_sentence, start, end)

        words = [ww for ww in (w.strip()
                               for w in re.split(r'\W+', this_sentence)) if ww]

        if len(words) > 0:
            translation = self.__find_translation(
                translated_sentences, sentence_context)
            if translation:
                sentence_context.translation = translation

        for word in words:
            yield (lt_pl.lemmatize(word.lower()), word, sentence_context)

    def count_words(self) -> Generator[WordStats, None, None]:
        files = []
        for file in os.listdir(self.subtitles_dir):
            files.append(self.subtitles_dir + "/" + file)
        files = sorted(files)
        vtt_files = [file for file in files if file.endswith(
            'pl.vtt') or file.endswith('pl[cc].vtt')]
        vtt_translate_files = [file for file in files if file.endswith(
            'de.vtt') or file.endswith('de[cc].vtt')]

        words = {}
        black_list = self.knowledge_base.get_black_list()

        for vtt_file_name, vtt_translate_file_name in zip(vtt_files, vtt_translate_files):
            lines = []
            with open(vtt_file_name) as vtt_file:
                lines = vtt_file.readlines()

            translated_lines = []
            with open(vtt_translate_file_name) as vtt_file:
                translated_lines = vtt_file.readlines()

            for word in self.__process_lines(lines, translated_lines):
                if black_list.get(word[0]):
                    continue
                if not words.get(word[0]):
                    words[word[0]] = WordOccurance(word[0])

                words[word[0]].add(word[1], word[2])

        total_occurances = sum((word.count for word in words.values()))
        current_count = 0
        for word in sorted(words.values(), key=lambda w: w.count, reverse=True):
            current_count += word.count
            yield WordStats(word, current_count/total_occurances)
