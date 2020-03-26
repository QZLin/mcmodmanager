from tkinter import BooleanVar, Frame, Checkbutton, Button, Text, END, Label, Tk, Canvas, Toplevel
from tkinter.ttk import Scrollbar, Frame

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

        container = Frame(root)
        ###
        canvas = Canvas(container, height='18c')
        scrollbar = Scrollbar(container, orient="vertical", command=canvas.yview)

        self.scroll_frame = scroll_frame = Frame(canvas)
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        container.pack(fill='both')
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ###
        frame1 = Frame(scroll_frame)
        a, b = get_jars()
        for x in a:
            opt = Option(frame1, x, True)
        for x in b:
            opt = Option(frame1, x[:-9])
        frame1.pack()
        ###

        ###
        frame2 = Frame(scroll_frame)
        Button(frame2, text='about', command=self.about).pack(side='left')
        bt_import = Button(frame2, text='导入Import', command=self.import_)
        bt_export = Button(frame2, text='导出Export', command=self.publish)
        bt_import.pack(side='left')
        bt_export.pack(side='right')
        frame2.pack()
        ###

        self.text = Text(scroll_frame, height=5, width=54)
        self.text.pack()

        if type(data) == dict:
            self.show_err(data['lost'])

    @staticmethod
    def about():
        tp = Toplevel()
        Label(tp, text='MC Mod Manager\nBy Q.Z.Lin').pack()

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
        result = compare(decode(code), get_jars())
        self.reload(result)


tk = Tk()
tk.title(TITLE)
app = App(tk)

tk.mainloop()
