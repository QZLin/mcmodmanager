import tkinter
import tkinter as tk
import tkinter.ttk as ttk
from base64 import b64decode, b16encode
from tkinter import BooleanVar, Frame, Checkbutton, Button, Text, END, Label, Tk, Canvas, Toplevel, ANCHOR
from tkinter.scrolledtext import ScrolledText
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
    def __init__(self, master=None):
        # build ui
        self.toplevel1 = tk.Tk() if master is None else tk.Toplevel(master)
        self.listbox_mods = tk.Listbox(self.toplevel1)
        self.var_modlist = tk.Variable(value=[])
        self.listbox_mods.configure(
            height=30, listvariable=self.var_modlist, selectmode="extended"
        )
        self.listbox_mods.pack(anchor="nw", expand=1, fill="both", side="top")
        self.frame_actions = ttk.Frame(self.toplevel1)
        self.button1 = ttk.Button(self.frame_actions)
        self.button1.configure(text="button1")
        self.button1.pack(side="left")
        self.button2 = ttk.Button(self.frame_actions)
        self.button2.configure(text="button2")
        self.button2.pack(side="left")
        self.button3 = ttk.Button(self.frame_actions)
        self.button3.configure(text="button3")
        self.button3.pack(side="left")
        self.button4 = ttk.Button(self.frame_actions)
        self.button4.configure(text="button4")
        self.button4.pack(side="left")
        self.button5 = ttk.Button(self.frame_actions)
        self.button5.configure(text="button5")
        self.button5.pack(side="left")
        self.frame_actions.configure(height=200, width=200)
        self.frame_actions.pack(expand=1, side="top")
        self.tkinter_scrolled_text = ScrolledText(self.toplevel1)
        self.tkinter_scrolled_text.configure(height=15, width=60)
        self.tkinter_scrolled_text.pack(expand=1, fill="x", side="top")
        self.toplevel1.configure(height=200, width=200)
        # self.toplevel1.bind("<MouseWheel>", self.callback, add="")

        # Main widget
        self.mainwindow = self.toplevel1

        # Bind widget event
        self.listbox_mods.bind('<<ListboxSelect>>', self.mod_list_changed)
        # self.listbox_mods.bind('<Double-1>', self.mod_list_double_click)

        # init status
        self.manage_mode = True
        self.modlist = []
        self.mod_status = {}
        #
        self.modlist_last_selection = []
        self.modlist_last_index = -1
        self.modlist_last_select_text = None

    def mod_list_double_click(self, event):
        print(event)

    def mod_list_changed(self, event):
        selection = list(self.listbox_mods.curselection())

        # print(selection)
        # modlist: list = list(self.var_modlist.get())

        def handle_index(index):
            name = self.modlist[index]
            self.mod_status[name] = not self.mod_status[name]
            display = self.render_item(name, self.mod_status[name])
            yv = self.listbox_mods.yview()
            self.listbox_mods.delete(index)
            self.listbox_mods.insert(index, display)
            self.listbox_mods.yview_moveto(yv[0])

            # def f(a=' ', b=' '): return modlist[index].replace(f'[{a}]', f'[{b}]', 1)
            #
            # modlist[index] = f(b='x') if (modlist[index][1] == ' ') else f('x')
            # self.var_modlist.set(modlist)
            self.modlist_last_index, self.modlist_last_select_text = index, display

        if selection == self.modlist_last_selection and \
                (clicked := self.listbox_mods.get(ANCHOR)) == self.modlist_last_select_text:
            handle_index(self.modlist_last_index)

        for i in [x for x in selection if x not in self.modlist_last_selection]:
            handle_index(i)
        # print('merge')
        # all_selected = list(selection)
        # all_selected.extend(self.last_selection)
        # for i in [x for x in all_selected if x not in selection or x not in self.last_selection]:
        #     print(modlist[i])
        self.modlist_last_selection = selection

    @staticmethod
    def render_item(name, is_active=True):
        return f'[{"x" if is_active else " "}] {name}'

    def update_mods(self):
        a, b = get_jars()
        modlist = list(a)
        modlist.extend(b)
        self.modlist = modlist
        self.mod_status = {name: (name in a) for name in modlist}
        for item in modlist:
            self.listbox_mods.insert(self.listbox_mods.size(), self.render_item(item, self.mod_status[item]))

        # for item in [f'[ ] {x}' for x in b]:
        #     self.listbox_mods.insert(-1, item)
        # for item in [f'[x] {x}' for x in a]:
        #     self.listbox_mods.insert(-1, item)
        # self.var_modlist.set([f'[x] {x}' for x in a] + [f'[ ] {x}' for x in b])

        # for x in a:
        #     Option(self.frame_mods, x, True)
        # for x in b:
        #     Option(self.frame_mods, x[:-9])

    @staticmethod
    def wx_tk_49():
        o0_oooo00_oooo0_o000 = Toplevel()
        o000_o000_o000_o00_o0 = Label(
            o0_oooo00_oooo0_o000, text=b64decode(
                b'TUMgTW9kIE1hbmFnZXIKTGljZW5zZTpHUEx2Mw'
                b'pCeSBRLlouTGluCm1haWw6cXpsaW4wMUAxNjMuY29t'
            ).decode())
        o000_o000_o000_o00_o0['text'] = \
            o000_o000_o000_o00_o0['text'] if b16encode(
                o000_o000_o000_o00_o0['text'].encode()) == b'4D43204D6F64204D616E616765720A4' \
                                                           b'C6963656E73653A47504C76330A4279205' \
                                                           b'12E5A2E4C696E0A6D61696C3A717A6C696E3' \
                                                           b'031403136332E636F6D' else ' '
        o000_o000_o000_o00_o0.grid()

    def publish(self):
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', encode(get_jars(True)))

    def show_err(self, result):
        for x in result:
            label = Label(self.scroll_frame, text='LostMod: ' + x, fg='red')
            label.pack(anchor='w')

    def reload(self, err_list=None):
        pass
        # self.root.destroy()
        # self.root = Tk()
        # self.root.title(TITLE)
        # App(self.root, {'lost': err_list} if type(err_list) == list else None)

    def import_(self):
        code = self.text.get('1.0', END)
        if code.strip() == '':
            raise RuntimeError('No code')
        result = compare(decode(code), get_jars())
        self.reload(result)

    def run(self):
        self.mainwindow.mainloop()


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

    # main = Tk()
    # main.title(TITLE)
    app = App()
    app.update_mods()
    app.run()
