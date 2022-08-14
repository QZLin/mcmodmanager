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


# class Option:
#     def __init__(self, root, text, clicked=False):
#         self.text = text
#         self.states = BooleanVar(value=clicked)
#         self.check_button = Checkbutton(root, text=text,
#                                         command=self.change, variable=self.states)
#         self.check_button.pack(anchor='w')
#
#     def change(self):
#         text = self.text
#         states = self.states.get()
#         if states:
#             handle_file(ENABLE, text)
#         else:
#             handle_file(DISABLE, text)
#
#     def set_text(self, text):
#         self.check_button['text'] = self.text = text


class App:
    def __init__(self, master=None, mod_manager=None):
        # build ui
        self.toplevel = tk.Tk() if master is None else tk.Toplevel(master)
        self.listbox_mods = tk.Listbox(self.toplevel)
        self.var_modlist = tk.Variable(value=[])
        self.listbox_mods.configure(
            height=30, listvariable=self.var_modlist, selectmode="extended"
        )
        self.listbox_mods.pack(anchor="nw", expand=1, fill="both", side="top")
        self.listbox_mods.bind("<<ListboxSelect>>", self.mod_list_changed, add="")
        self.frame_actions = ttk.Frame(self.toplevel)
        self.button_manage_mode = ttk.Button(self.frame_actions)
        self.button_manage_mode.configure(takefocus=False, text="Manage")
        self.button_manage_mode.pack(side="left")
        self.button_manage_mode.bind("<1>", self.callback, add="")
        self.button2 = ttk.Button(self.frame_actions)
        self.button2.configure(text="Mark")
        self.button2.pack(side="left")
        self.button2.bind("<1>", self.callback, add="")
        self.button_import = ttk.Button(self.frame_actions)
        self.button_import.configure(text="Import")
        self.button_import.pack(side="left")
        self.button_import.bind("<1>", self.callback, add="")
        self.button_export = ttk.Button(self.frame_actions)
        self.button_export.configure(text="Export")
        self.button_export.pack(side="left")
        self.button_export.bind("<1>", self.callback, add="")
        self.button_about = ttk.Button(self.frame_actions)
        self.button_about.configure(text="About")
        self.button_about.pack(side="left")
        self.button_about.bind("<1>", self.callback, add="")
        self.frame_actions.configure(height=200, width=200)
        self.frame_actions.pack(expand=1, side="top")
        self.tkinter_scrolled_text = ScrolledText(self.toplevel)
        self.tkinter_scrolled_text.configure(height=15, width=60)
        self.tkinter_scrolled_text.pack(expand=1, fill="x", side="top")
        self.entry_output = ttk.Entry(self.toplevel)
        self.entry_output.pack(expand=1, fill="x", side="bottom")
        self.toplevel.configure(height=200, width=200)
        self.toplevel.title("MC Mod Manager")

        # Main widget
        self.mainwindow = self.toplevel

        # Bind widget event
        # self.listbox_mods.bind('<<ListboxSelect>>', self.mod_list_changed)
        # self.listbox_mods.bind('<Double-1>', self.mod_list_double_click)
        # self.button_manage_mode.bind('<Button-1>', self.callback)
        # self.button_export.bind('<Button-1>', self.callback)

        # init status
        self.manage_mode = True
        self.modlist = []
        self.filelist = []
        self.mod_status = {}
        #
        self.modlist_last_selection = []
        self.modlist_last_index = -1
        self.modlist_last_select_text = None

        self.manager: ModManager = mod_manager

    def mod_list_double_click(self, event):
        print(event)

    def mod_list_changed(self, event):
        if not self.manage_mode:
            return
        selection = list(self.listbox_mods.curselection())

        def handle_index(index):
            name = self.modlist[index]
            self.mod_status[name] = not self.mod_status[name]

            display = self.render_item(name, self.mod_status[name])
            yv = self.listbox_mods.yview()
            self.listbox_mods.delete(index)
            self.listbox_mods.insert(index, display)
            self.listbox_mods.yview_moveto(yv[0])

            self.manager.handle_file(self.mod_status[name], self.filelist[index])
            self.filelist[index] = self.manager.ext_name(self.filelist[index], self.mod_status[name])

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
        self.load_files()

    @staticmethod
    def render_item(name, is_active=True):
        return f'[{"x" if is_active else " "}] {name}'

    def info(self, text):
        self.entry_output.delete(0, tk.END)
        self.entry_output.insert(0, text)

    def load_files(self):
        pass
        # self.manager = Manager()

    def update_mods(self):
        a, b = self.manager.get_files()
        self.filelist = list(a)
        self.filelist.extend(b)
        modlist = self.manager.mod_names()
        self.modlist = modlist
        self.mod_status = {name: (name in a) for name in modlist}
        for item in modlist:
            self.listbox_mods.insert(self.listbox_mods.size(), self.render_item(item, self.mod_status[item]))

    def callback(self, event):
        match event.widget:
            case self.button_manage_mode:
                self.manage_mode = not self.manage_mode
                self.info(f'Manage Mode:{self.manage_mode}')
            case self.button_export:
                self.tkinter_scrolled_text.delete('1.0', tk.END)
                self.tkinter_scrolled_text.insert('1.0', ModManager.encode(self.manager.get_files(True)))
                self.info('Exported...')
            case self.button_import:
                pass

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

    # def publish(self):
    #     self.text.delete('1.0', 'end')
    #     self.text.insert('1.0', Manager.encode(get_jars(True)))

    # def show_err(self, result):
    #     for x in result:
    #         label = Label(self.scroll_frame, text='LostMod: ' + x, fg='red')
    #         label.pack(anchor='w')

    def reload(self, err_list=None):
        pass
        # self.root.destroy()
        # self.root = Tk()
        # self.root.title(TITLE)
        # App(self.root, {'lost': err_list} if type(err_list) == list else None)

    # def import_(self):
    #     code = self.text.get('1.0', END)
    #     if code.strip() == '':
    #         raise RuntimeError('No code')
    #     result = compare(decode(code), get_jars())
    #     self.reload(result)

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
    parser.add_argument('-p', '--path', type=str, default='.', help='Path of minecraft mods')

    args = parser.parse_args()

    # if args.path:
    #     ModManager.MOD_DIR = parser.parse_args().path

    app = App(mod_manager=ModManager(args.path))
    app.update_mods()
    app.run()