from tkinter import BooleanVar, Checkbutton, Frame, Button, Text, END, Label, Tk

from ModManager import *


class Option:
    def __init__(self, root, text, clicked=False):
        self.text = text
        self.states = BooleanVar(value=clicked)
        self.cbt = Checkbutton(root, text=text, command=self.change, variable=self.states)

        self.cbt.pack(anchor='w')

    def change(self):
        text = self.text
        states = self.states.get()
        if states:
            handle_file(ENABLE, text)
        else:
            handle_file(DISABLE, text)

    def set_text(self, text):
        self.text = text
        self.cbt['text'] = text


class App:

    def __init__(self, root):
        self.root = root
        a, b = get_jars()
        for x in a:
            opt = Option(root, x, True)
        for x in b:
            opt = Option(root, x[:-9])

        ###
        frame2 = Frame(root)
        bt = Button(frame2, text='Import', command=self.import_)
        bt2 = Button(frame2, text='Publish', command=self.publish)
        bt.pack(side='left')
        bt2.pack(side='right')
        frame2.pack()
        ###

        self.text = Text(root, height=5, width=50)
        self.text.pack()

    def publish(self):
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', encode(get_jars(True)))

    def import_(self):
        global tk
        code = self.text.get('1.0', END).replace('\n', '')
        result = compare(decode(code), get_jars())
        if type(result) == list:
            for x in result:
                label = Label(text=x, fg='red')
                label.pack(anchor='w')
        tk.destroy()
        tk = Tk()
        tk.title('mcmodmanager')
        app = App(tk)


tk = Tk()
tk.title('mcmodmanager')
app = App(tk)

tk.mainloop()
