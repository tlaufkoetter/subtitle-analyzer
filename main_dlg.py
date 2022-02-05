import word_counter
import os
import wx


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

    def load(self):
        if self.word_counter is None:
            return

        self.list_ctrl.ClearAll()
        self.list_ctrl.InsertColumn(0, 'rank')
        self.list_ctrl.InsertColumn(1, 'count')
        self.list_ctrl.InsertColumn(2, 'word', width=100)
        self.list_ctrl.InsertColumn(3, 'percentile')
        self.list_ctrl.InsertColumn(4, 'context', width=400)
        self.list_ctrl.InsertColumn(5, 'translation', width=400)

        occurances = list(self.word_counter.count_words())
        occs = {word.word_occurance.word: word.word_occurance.count for word in occurances}
        for index, word_stat in enumerate(occurances):
            word_occurance = word_stat.word_occurance
            word = word_occurance.word
            self.list_ctrl.InsertItem(index, index + 1)
            self.list_ctrl.SetItem(index, 0, str(index + 1))
            self.list_ctrl.SetItem(index, 1, str(word_occurance.count))
            self.list_ctrl.SetItem(index, 2, word)
            self.list_ctrl.SetItem(index, 3, "{:.2f}".format(100*word_stat.percentile))

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
