import word_counter
import os
import wx


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
            self, size=(300, 200), value=sentence, style=wx.TE_MULTILINE)
        main_sizer.Add(self.sentence_text, flag=wx.EXPAND)

        self.translation_text = wx.TextCtrl(
            self, size=(300, 200),  value=translation, style=wx.TE_MULTILINE)
        main_sizer.Add(self.translation_text, flag=wx.EXPAND)

        word_button = wx.Button(self, label='Word Card')
        word_button.Bind(wx.EVT_BUTTON, self.on_word)
        main_sizer.Add(word_button, flag=wx.EXPAND)

        sentence_button = wx.Button(self, label='Sentence Card')
        sentence_button.Bind(wx.EVT_BUTTON, self.on_sentence)
        main_sizer.Add(sentence_button, flag=wx.EXPAND)

        self.SetSizer(main_sizer)
        self.SetSize(height=600, width=800)

    def _export_to_csv(self, file):
        with open(file, 'a+') as word_cards_file:
            word_cards_file.write('{}\t{}\t{}\t{}\n'.format(
                self.word_text.GetValue(),
                self.translated_word_text.GetValue(),
                self.sentence_text.GetValue(),
                self.translation_text.GetValue()
            ))
        self.callback()

    def on_word(self, event):
        self._export_to_csv('word_cards.csv')
        self.Close()

    def on_sentence(self, event):
        self._export_to_csv('sentence_cards.csv')
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

    def _update_list(self, update):
        if self.word_counter is None:
            return

        known_words = []
        sel_index = self.list_ctrl.GetFirstSelected()
        while sel_index != -1:
            t = self.list_ctrl.GetItemText(sel_index, 2)
            known_words.append(t)
            sel_index = self.list_ctrl.GetNextSelected(sel_index)

        update(known_words)
        self.load()

    def on_blacklist(self, event):
        self._update_list(self.word_counter.update_black_list)

    def on_reload(self, event):
        self._update_list(self.word_counter.update_known_words)

    def on_click(self, event):
        item: wx.ListItem = event.Item
        index = item.Id

        word = self.occurances[index]
        occs = {
            word.word_occurance.word: word.word_occurance.count for word in self.occurances}
        context = word.word_occurance.get_context(occs)
        word_window = WordFrame(
            self, word.word_occurance.word, str(context), context.translation, lambda: self.load(False))

        word_window.Show()

    def load(self, reload=True):
        if self.word_counter is None:
            return

        cards = {}
        if os.path.isfile('word_cards.csv'):
            with open('word_cards.csv', 'r') as cards_file:
                for line in cards_file.readlines():
                    word = line.split('\t')[0]
                    if word:
                        cards[word.lower()] = True

            with open('sentence_cards.csv', 'r') as cards_file:
                for line in cards_file.readlines():
                    word = line.split('\t')[0]
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

        self.occurances = [word for word in self.occurances if not cards.get(
            word.word_occurance.word)]
        occs = {
            word.word_occurance.word: word.word_occurance.count for word in self.occurances}
        for index, word_stat in enumerate(self.occurances):
            word_occurance = word_stat.word_occurance
            word = word_occurance.word
            self.list_ctrl.InsertItem(index, index + 1)
            self.list_ctrl.SetItem(index, 0, str(index + 1))
            self.list_ctrl.SetItem(index, 1, str(word_occurance.count))
            self.list_ctrl.SetItem(index, 2, word)
            self.list_ctrl.SetItem(
                index, 3, "{:.2f}".format(100*word_stat.percentile))

            context = word_occurance.get_context(occs)

            self.list_ctrl.SetItem(index, 4, str(context))
            self.list_ctrl.SetItem(index, 5, context.translation or '')

    def on_press(self, event):
        with wx.DirDialog(self, message="Choose a folder") as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.word_counter = word_counter.WordCounter(
                    'known.csv', 'black_list.csv', dlg.GetPath())
            dlg.Destroy()

        self.load()
