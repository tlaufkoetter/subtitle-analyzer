
import os
from typing import Generator
import lemmagen3
import re
import requests

lt_pl = lemmagen3.Lemmatizer('pl')


class SentenceContext:
    def __init__(self, sentence, start, end):
        self.sentence = sentence
        self.before = None
        self.after = None
        self.start = start
        self.end = end
        self.translation = None

    def __str__(self) -> str:
        text = ""
        if self.before:
            text += self.before + "\n"

        text += self.sentence

        if self.after:
            text += "\n" + self.after

        return self.sentence

    def __lt__(self, other):
        return self.start < other.start


class WordOccurance:
    def __init__(self, word):
        self.count = 0
        self.word = word
        self.forms = {}
        self.sentences = {}
        self.sentence_contexts = []

    def add(self, form, sentence_context: SentenceContext):
        self.count += 1
        if self.forms.get(form) is None:
            self.forms[form] = 0

        self.forms[form] += 1

        self.sentence_contexts.append(sentence_context)

    def _average(self, lis):
        return sum(lis) / len(lis)

    def get_context(self, word_occurances):
        di = ((context, sum([(word_occurances.get(lt_pl.lemmatize(word.lower())) or 0) for word in re.split(
            r'\W+', str(context))])) for context in self.sentence_contexts)
        # di = ((context, len(str(context))) for context in self.sentence_contexts)
        return max(di, key=lambda c: c[1])[0]


class WordStats:
    def __init__(self, word_occurance: WordOccurance, percentile):
        self.word_occurance = word_occurance
        self.percentile = percentile


class WordCounter:
    def __init__(self, known_words_file_name, black_list_file_name, subtitles_dir):
        self.known_words_file_name = known_words_file_name
        self.subtitles_dir = subtitles_dir
        self.black_list_file_name = black_list_file_name

    def _process_lines(self, lines, translated_lines):
        has_started = False

        translated_sentences = []
        start = (0, 0, 0, 0)
        end = (0, 0, 0, 0)
        this_sentence = None
        for line in translated_lines:
            if re.match(r'^\s*$', line):
                translated_sentences.append((this_sentence, start, end))
                has_started = False
                start = (0, 0, 0, 0)
                end = (0, 0, 0, 0)
                this_sentence = None
            elif has_started and re.match(r'^\d\d:\d\d:\d\d', line):
                m = re.match(
                    r'^(\d\d):(\d\d):(\d\d).(\d\d\d) --> (\d\d):(\d\d):(\d\d).(\d\d\d)', line)
                if m:
                    start = (int(m.group(1)), int(m.group(2)),
                             int(m.group(3)), int(m.group(4)))
                    end = (int(m.group(5)), int(m.group(6)),
                           int(m.group(7)), int(m.group(8)))
            elif has_started:
                text_line = re.sub(r'<[^>]+>', '', line)
                text_line = re.sub(r'\[[^\]]+\]', '', text_line)
                text_line = re.sub(r'- ?', '', text_line)
                text_line = text_line.strip()
                if not this_sentence:
                    this_sentence = text_line
                else:
                    this_sentence += ' ' + text_line

            elif re.match(r'^\d+$', line):
                has_started = True

        has_started = False
        previous_line = None

        sentences = [None]
        all_sentences = []
        start = (0, 0, 0, 0)
        end = (0, 0, 0, 0)
        this_sentence = None
        for line in lines:
            if has_started and re.match(r'^\d\d:\d\d:\d\d', line):
                m = re.match(
                    r'^(\d\d):(\d\d):(\d\d).(\d\d\d) --> (\d\d):(\d\d):(\d\d).(\d\d\d)', line)
                if m:
                    start = (int(m.group(1)), int(m.group(2)),
                             int(m.group(3)), int(m.group(4)))
                    end = (int(m.group(5)), int(m.group(6)),
                           int(m.group(7)), int(m.group(8)))
            elif re.match(r'^\s*$', line):

                if this_sentence:
                    if sentences[-1] is not None:
                        sentences[-1].after = this_sentence
                    sent = None
                    sentence_context = SentenceContext(
                        this_sentence, start, end)
                    for word in (ww for ww in (w.strip() for w in re.split(r'\W+', this_sentence)) if ww):
                        sentence_context.after = previous_line
                        sent = sentence_context
                        all_sentences.append((lt_pl.lemmatize(
                            word.lower()), word, sentence_context))
                    if sent:

                        ft = None
                        lt = None
                        found = True
                        for i, trans in enumerate(translated_sentences):
                            if trans[1] <= sentence_context.start and trans[2] >= sentence_context.start or sentence_context.start <= trans[1] and sentence_context.end >= trans[1]:
                                ft = i, trans[0]
                            if trans[1] <= sentence_context.end and trans[2] >= sentence_context.end:
                                lt = i, trans[0]

                            if ft is not None:
                                break
                        else:
                            found = False

                        if found:
                            if ft == lt or lt is None:
                                tt = ft[1]  # t1 + ' ' + ft[1] + ' ' + t2
                            else:
                                # t1 + ' ' + ft[1] + ' ' + lt[1] + ' ' + t2
                                tt = ft[1] + ' ' + lt[1]

                            sentence_context.translation = tt
                        sentences.append(sent)
                    previous_line = this_sentence
                has_started = False
                start = (0, 0, 0, 0)
                end = (0, 0, 0, 0)
                this_sentence = None
            elif has_started:
                text_line = re.sub(r'<[^>]+>', '', line)
                text_line = re.sub(r'\[[^\]]+\]', '', text_line)
                text_line = text_line.replace('- ', '')
                text_line = text_line.strip()
                if this_sentence:
                    this_sentence += ' ' + text_line
                else:
                    this_sentence = text_line

            elif re.match(r'^\d+$', line):
                has_started = True
        return all_sentences

    def _load_words(self, file_name):
        with open(file_name, 'r') as known_file:
            return {l.strip(): True for l in known_file.readlines()}

    def update_words(self, words, file_name):
        known = self._load_words(file_name)

        with open(file_name, 'w') as known_file:
            for word in words:
                known[word] = True

            known_file.writelines([k + '\n' for k in known.keys()])

    def update_known_words(self, known_words):
        self.update_words(known_words, self.known_words_file_name)

    def update_black_list(self, black_list):
        self.update_words(black_list, self.black_list_file_name)

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
        known = self._load_words(self.known_words_file_name)
        black_list = self._load_words(self.black_list_file_name)

        for vtt_file_name, vtt_translate_file_name in zip(vtt_files, vtt_translate_files):
            lines = []
            with open(vtt_file_name) as vtt_file:
                lines = vtt_file.readlines()

            translated_lines = []
            with open(vtt_translate_file_name) as vtt_file:
                translated_lines = vtt_file.readlines()

            print(vtt_file_name)
            print(vtt_translate_file_name)
            print('\n')

            for word in self._process_lines(lines, translated_lines):
                if black_list.get(word[0]):
                    continue
                if not words.get(word[0]):
                    words[word[0]] = WordOccurance(word[0])

                words[word[0]].add(word[1], word[2])

        total_occurances = sum((word.count for word in words.values()))
        current_count = 0
        for word in sorted(words.values(), key=lambda w: w.count, reverse=True):
            current_count += word.count
            if not known.get(word.word):
                yield WordStats(word, current_count/total_occurances)
