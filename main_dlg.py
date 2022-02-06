import word_counter
import os
import wx
import pandas
import re
from pathlib import Path

home_path = str(Path.home())
user_path = os.path.join(home_path, '.subtitle_analyzer/')
if not os.path.exists(user_path):
    os.mkdir(user_path)

word_cards_file = os.path.join(user_path, 'word_cards.csv')
known_file = os.path.join(user_path, 'known.csv')
black_list_file = os.path.join(user_path, 'black_list.csv')


class WordFrame(wx.Frame):
    def __init__(self, parent, word, sentence, translation, callback):
        super().__init__(parent=parent, title=word)
        self.callback = callback
        self.result = False
        main_sizer = wx.FlexGridSizer(rows=5, cols=2, vgap=10, hgap=10)
        main_sizer.FitInside(self)

        self.word_text = wx.TextCtrl(self, value=word)
        main_sizer.Add(self.word_text, flag=wx.EXPAND)

        self.translated_word_text = wx.TextCtrl(self)
        main_sizer.Add(self.translated_word_text, flag=wx.EXPAND)

        self.sentence_text = wx.TextCtrl(
            self, size=(350, 300), value=sentence, style=wx.TE_MULTILINE)
        main_sizer.Add(self.sentence_text, flag=wx.EXPAND)

        self.translation_text = wx.TextCtrl(
            self, size=(350, 300),  value=translation, style=wx.TE_MULTILINE)
        main_sizer.Add(self.translation_text, flag=wx.EXPAND)

        word_button = wx.Button(self, label='Word Card')
        word_button.Bind(wx.EVT_BUTTON, self.on_word)
        main_sizer.Add(word_button, flag=wx.EXPAND)

        sentence_button = wx.Button(self, label='Sentence Card')
        sentence_button.Bind(wx.EVT_BUTTON, self.on_sentence)
        main_sizer.Add(sentence_button, flag=wx.EXPAND)

        self.SetSizer(main_sizer)
        self.SetSize(height=600, width=800)

    def _export_to_csv(self, is_word_card):
        data = pandas.DataFrame([[
            re.sub(r'\n+', '', self.word_text.GetValue()).strip(),
            re.sub(r'\n+', '', self.translated_word_text.GetValue()).strip(),
            re.sub(r'\n+', '', self.sentence_text.GetValue()).strip(),
            re.sub(r'\n+', '', self.translation_text.GetValue()).strip(),
            is_word_card
        ]])

        with open(word_cards_file, mode='a') as f:
            data.to_csv(f, header=False, index=False)
        self.callback()

    def on_word(self, event):
        self._export_to_csv(True)
        self.Close()

    def on_sentence(self, event):
        self._export_to_csv(False)
        self.Close()


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='Subtitle Analyzer')
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.row_obj_dict = {}
        self.word_counter = None

        self.list_ctrl = wx.ListCtrl(
            self, size=(-1, 400),
            style=wx.LC_REPORT | wx.BORDER_SUNKEN
        )

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_click, self.list_ctrl)
        main_sizer.Add(self.list_ctrl, 0, wx.ALL | wx.EXPAND, 5)
        edit_button = wx.Button(self, label='Load Subtitles')
        edit_button.Bind(wx.EVT_BUTTON, self.on_press)
        main_sizer.Add(edit_button, 0, wx.ALL | wx.CENTER, 5)
        reload_button = wx.Button(self, label='Mark As Known')
        reload_button.Bind(wx.EVT_BUTTON, self.on_reload)
        main_sizer.Add(reload_button, 0, wx.ALL | wx.CENTER, 5)
        blacklist_button = wx.Button(self, label='Add To Blacklist')
        blacklist_button.Bind(wx.EVT_BUTTON, self.on_blacklist)
        main_sizer.Add(blacklist_button, 0, wx.ALL | wx.CENTER, 5)
        self.SetSizer(main_sizer)
        self.SetSize(height=600, width=800)

    def _update_list(self, update, reload=False):
        if self.word_counter is None:
            return

        known_words = []
        sel_index = self.list_ctrl.GetFirstSelected()
        while sel_index != -1:
            t = self.list_ctrl.GetItemText(sel_index, 2)
            known_words.append(t)
            sel_index = self.list_ctrl.GetNextSelected(sel_index)

        update(known_words)
        self.load(reload)

    def on_blacklist(self, event):
        self._update_list(self.word_counter.update_black_list, True)

    def on_reload(self, event):
        self._update_list(self.word_counter.update_known_words)

    def on_click(self, event):
        item: wx.ListItem = event.Item
        index = item.Id

        word = self.occurances[index]
        contexts = word.word_occurance.get_context(
            self.word_counter.get_known_words())
        word_window = WordFrame(
            self, word.word_occurance.word, str.join('\n\n', [str(context[0]) for context in contexts][:10]), str.join('\n\n', [context[0].translation for context in contexts][:10]), lambda: self.load(False))

        word_window.Show()

    def load(self, reload=True):
        if self.word_counter is None:
            return

        cards = {}
        if os.path.isfile(word_cards_file):
            csv = pandas.read_csv(
                word_cards_file, index_col=False, header=None)
            for line in csv.iterrows():
                word = line[1][0]
                print(word)
                if word:
                    cards[word.lower()] = True

        self.list_ctrl.ClearAll()
        self.list_ctrl.InsertColumn(0, 'rank')
        self.list_ctrl.InsertColumn(1, 'count')
        self.list_ctrl.InsertColumn(2, 'word', width=100)
        self.list_ctrl.InsertColumn(3, 'percentile')
        self.list_ctrl.InsertColumn(4, 'context', width=400)
        self.list_ctrl.InsertColumn(5, 'translation', width=400)

        if reload:
            self.occurances = list(self.word_counter.count_words())

        known_words = self.word_counter.get_known_words()
        self.occurances = [word for word in self.occurances if not cards.get(
            word.word_occurance.word) and word.word_occurance.word not in known_words]
        for index, word_stat in enumerate(self.occurances):
            word_occurance = word_stat.word_occurance
            word = word_occurance.word
            self.list_ctrl.InsertItem(index, index + 1)
            self.list_ctrl.SetItem(index, 0, str(index + 1))
            self.list_ctrl.SetItem(index, 1, str(word_occurance.count))
            self.list_ctrl.SetItem(index, 2, word)
            self.list_ctrl.SetItem(
                index, 3, "{:.2f}".format(100*word_stat.percentile))

            context = word_occurance.get_context(known_words)[0][0]

            self.list_ctrl.SetItem(index, 4, str(context))
            self.list_ctrl.SetItem(index, 5, context.translation or '')

    def on_press(self, event):
        with wx.DirDialog(self, message="Choose a folder") as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.word_counter = word_counter.WordCounter(
                    known_file, black_list_file, dlg.GetPath())
            dlg.Destroy()

        self.load()
