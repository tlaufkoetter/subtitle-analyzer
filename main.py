from pathlib import Path
import wx
from knowledge_base import KnowledgeBase
from card_exporter import CardExporter
from main_dlg import MainFrame
import os

home_path = str(Path.home())
user_path = os.path.join(home_path, 'subtitle_analyzer/')

if not os.path.exists(user_path):
    os.mkdir(user_path)

word_cards_file = os.path.join(user_path, 'word_cards.csv')


def main():
    app = wx.App()
    frame = MainFrame(KnowledgeBase(user_path), CardExporter(user_path))
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
