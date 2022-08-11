import tkinter
from base64 import b64decode, b16encode
from tkinter import BooleanVar, Frame, Checkbutton, Button, Text, END, Label, Tk, Canvas, Toplevel
from tkinter.ttk import Scrollbar, Frame
import argparse

import ModManager
from ModManager import *

TITLE = 'MC Mod Manager'


class Option:
    def __init__(self, root, text, clicked=False):
        self.text = text
        self.states = BooleanVar(value=clicked)
        self.check_button = Checkbutton(root, text=text,
                                        command=self.change, variable=self.states)
        self.check_button.pack(anchor='w')

    def change(self):
        text = self.text
        states = self.states.get()
        if states:
            handle_file(ENABLE, text)
        else:
            handle_file(DISABLE, text)

    def set_text(self, text):
        self.check_button['text'] = self.text = text


class App:
    def __init__(self, root, data=None):
        self.root = root

        self.container = Frame(root)
        ###
        self.canvas = Canvas(self.container, height='18c')
        self.scrollbar = Scrollbar(self.container, orient="vertical", command=self.canvas.yview)

        self.scroll_frame = Frame(self.canvas)
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.container.pack(fill='both')
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        ###
        self.frame_mods = Frame(self.scroll_frame)
        # choices_var = tkinter.StringVar(value=a)
        # listbox = tkinter.Listbox(self.frame_mods, selectmode='extended', listvariable=choices_var)
        # listbox.pack(fill='both', expand=True)
        self.frame_mods.pack()
        ###

        ###
        self.frame_action = Frame(self.scroll_frame)
        Button(self.frame_action, text='关于About', command=self.wx_tk_49).pack(side='left')
        bt_import = Button(self.frame_action, text='导入Import', command=self.import_)
        bt_export = Button(self.frame_action, text='导出Export', command=self.publish)
        bt_import.pack(side='left')
        bt_export.pack(side='right')
        self.frame_action.pack()
        ###

        self.text = Text(self.scroll_frame, height=5, width=54)
        self.text.pack()

        if type(data) == dict:
            self.show_err(data['lost'])

        self.update_mods()

    def update_mods(self):
        a, b = get_jars()

        for x in a:
            Option(self.frame_mods, x, True)
        for x in b:
            Option(self.frame_mods, x[:-9])

    @staticmethod
    def wx_tk_49():
        O0OOOO00OOOO0O000 = Toplevel()
        O000O000O000O00O0 = \
            Label(O0OOOO00OOOO0O000, text=b64decode(
                b'TUMgTW9kIE1hbmFnZXIKTGljZW5zZTpHUEx2Mw'
                b'pCeSBRLlouTGluCm1haWw6cXpsaW4wMUAxNjMuY29t'
            ).decode())
        O000O000O000O00O0['text'] = \
            O000O000O000O00O0['text'] \
                if b16encode(
                O000O000O000O00O0['text'].encode()
            ) == \
                   b'4D43204D6F64204D616E616765720A4' \
                   b'C6963656E73653A47504C76330A4279205' \
                   b'12E5A2E4C696E0A6D61696C3A717A6C696E3031403136332E636F6D' \
                else ' '
        O000O000O000O00O0.pack()

    def publish(self):
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', encode(get_jars(True)))

    def show_err(self, result):
        for x in result:
            label = Label(self.scroll_frame, text='LostMod: ' + x, fg='red')
            label.pack(anchor='w')

    def reload(self, err_list=None):
        self.root.destroy()
        self.root = Tk()
        self.root.title(TITLE)
        App(self.root, {'lost': err_list} if type(err_list) == list else None)

    def import_(self):
        code = self.text.get('1.0', END).replace('\n', '')
        if code.strip() == '':
            raise RuntimeError('No code')
        result = compare(decode(code), get_jars())
        self.reload(result)


# def read_config():
#     config = ConfigParser()
#     config.read('config.ini')
#     try:
#         set_root(config.get('config', 'jar_path'))
#     except (NoSectionError, NoOptionError):
#         with open('config.ini', 'w') as file:
#             file.write('[config]\njar_path=../')


# read_config()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', type=str, help='Path of minecraft mods')

    args = parser.parse_args()

    if args.path:
        ModManager.MOD_DIR = parser.parse_args().path

    tk = Tk()
    tk.title(TITLE)
    app = App(tk)

    tk.mainloop()
