import wx
from main_dlg import MainFrame


def main():
    app = wx.App()
    frame = MainFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
