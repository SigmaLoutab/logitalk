from customtkinter import *
from PIL import Image, ImageTk
import socket
import threading
from tkinter import filedialog
import base64
import os


# === Вікно чату ===
class MainWindow(CTk):
    def __init__(self, username, avatar_path, host="6.tcp.eu.ngrok.io", port=12287):
        super().__init__()


        self.geometry('500x400')
        self.title("Chat Client")


        self.username = username
        self.avatar_path = avatar_path
        self.avatars = {}  # {username: CTkImage}


        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((host, port))
        except Exception as e:
            print("❌ Не вдалося підключитися:", e)
            self.destroy()
            return


        # === Ліва панель (нік і аватар) ===
        self.sidebar = CTkFrame(self, width=140)
        self.sidebar.pack(side=LEFT, fill=Y)


        # аватар користувача
        self.avatar_img = CTkImage(Image.open(self.avatar_path).resize((80, 80)))
        self.avatar_label = CTkLabel(self.sidebar, image=self.avatar_img, text="")
        self.avatar_label.pack(pady=10)


        self.change_avatar_btn = CTkButton(self.sidebar, text="Змінити аватар", command=self.changeAvatar)
        self.change_avatar_btn.pack(pady=5, padx=10)


        # нік
        self.entry = CTkEntry(self.sidebar, placeholder_text="Ім’я")
        self.entry.insert(0, username)
        self.entry.pack(pady=10, padx=10)


        self.save_button = CTkButton(self.sidebar, text="Зберегти нік", command=self.saveName)
        self.save_button.pack(pady=10, padx=10)


        # === Основна панель (чат) ===
        self.chat_frame = CTkFrame(self)
        self.chat_frame.pack(side=LEFT, fill=BOTH, expand=True)


        self.chat_box = CTkScrollableFrame(self.chat_frame)
        self.chat_box.pack(fill=BOTH, expand=True, padx=10, pady=10)


        self.message_entry = CTkEntry(self.chat_frame, placeholder_text="Введіть повідомлення:")
        self.message_entry.pack(fill=X, padx=10, pady=5, side=LEFT, expand=True)


        self.send_button = CTkButton(self.chat_frame, text=">", width=40, command=self.sendMessage)
        self.send_button.pack(side=LEFT, padx=5, pady=5)


        # === Нова кнопка для файлів ===
        self.file_button = CTkButton(self.chat_frame, text="📎", width=40, command=self.sendFile)
        self.file_button.pack(side=LEFT, padx=5, pady=5)


        # === Потік для отримання повідомлень ===
        threading.Thread(target=self.receiveMessages, daemon=True).start()


        # Відправляємо серверу аватар
        self.sendAvatarChange(self.avatar_path)


    def add_message(self, author, message):
        frame = CTkFrame(self.chat_box)
        frame.pack(fill=X, pady=2, padx=5, anchor="w")


        img = self.avatars.get(author)
        if img:
            lbl_avatar = CTkLabel(frame, image=img, text="")
            lbl_avatar.pack(side=LEFT, padx=5)


        lbl_text = CTkLabel(frame, text=f"{author}: {message}",
                            anchor="w", justify="left", wraplength=300)
        lbl_text.pack(side=LEFT, fill=X, expand=True)


    def add_system_message(self, message):
        frame = CTkFrame(self.chat_box, fg_color="transparent")
        frame.pack(fill=X, pady=2, padx=5, anchor="center")


        lbl_text = CTkLabel(frame, text=message, anchor="center", justify="center",
                            text_color="gray", font=("Helvetica", 12, "italic"))
        lbl_text.pack(fill=X, expand=True)


    def saveName(self):
        new_name = self.entry.get().strip()
        if new_name:
            data = f"NICK@{self.username}@{new_name}\n"
            try:
                self.sock.sendall(data.encode())
                self.username = new_name
            except:
                self.add_message("System", "⚠️ З’єднання з сервером втрачено!")


    def changeAvatar(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if path:
            self.avatar_path = path
            self.avatar_img = CTkImage(Image.open(self.avatar_path).resize((80, 80)))
            self.avatar_label.configure(image=self.avatar_img)
            self.sendAvatarChange(path)


    def sendAvatarChange(self, path):
        try:
            data = f"AVATAR@{self.username}@{path}\n"
            self.sock.sendall(data.encode())
        except:
            self.add_message("System", "⚠️ Не вдалося відправити аватар.")


    def sendMessage(self):
        message = self.message_entry.get().strip()
        if message:
            data = f"TEXT@{self.username}@{message}\n"
            try:
                self.sock.sendall(data.encode())
                self.message_entry.delete(0, 'end')
            except:
                self.add_message("System", "⚠️ Не вдалося відправити повідомлення — сервер недоступний.")


    def sendFile(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        try:
            with open(path, "rb") as f:
                raw = f.read()
            encoded = base64.b64encode(raw).decode("utf-8")
            filename = os.path.basename(path)
            data = f"FILE@{self.username}@{filename}@{len(raw)}@{encoded}\n"
            self.sock.sendall(data.encode())
            self.add_system_message(f"📤 Ви відправили файл {filename}")
        except Exception as e:
            self.add_system_message(f"⚠️ Не вдалося надіслати файл: {e}")


    def receiveMessages(self):
        buffer = ""
        while True:
            try:
                data = self.sock.recv(1024).decode()
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.processMessage(line.strip())
            except:
                break


    def processMessage(self, line):
        parts = line.split("@", 4)
        if parts[0] == "TEXT" and len(parts) == 3:
            author, message = parts[1], parts[2]
            self.add_message(author, message)
        elif parts[0] == "NICK" and len(parts) == 3:
            old, new = parts[1], parts[2]
            self.add_system_message(f"🔔 {old} тепер {new}")
        elif parts[0] == "AVATAR" and len(parts) == 3:
            user, path = parts[1], parts[2]
            try:
                self.avatars[user] = CTkImage(Image.open(path).resize((40, 40)))
                self.add_system_message(f"🖼 {user} змінив аватар")
            except:
                self.add_system_message(f"⚠️ Не вдалося завантажити аватар {user}")
        elif parts[0] == "FILE" and len(parts) == 5:
            user, filename, size, encoded = parts[1], parts[2], parts[3], parts[4]
            try:
                raw = base64.b64decode(encoded.encode("utf-8"))
                save_dir = "downloads"
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, filename)
                with open(save_path, "wb") as f:
                    f.write(raw)
                self.add_system_message(f"📥 {user} надіслав файл {filename} ({size} байт). Збережено у {save_path}")
            except Exception as e:
                self.add_system_message(f"⚠️ Помилка отримання файлу {filename}: {e}")




# === Вікно входу ===
class AuthWindow(CTk):
    def __init__(self):
        super().__init__()
        self.geometry('700x400')
        self.title('Вхід')
        self.resizable(True, False)


        self.avatar_path = "default.png"


        self.left_frame = CTkFrame(self)
        self.left_frame.pack(side='left', fill='both')


        img_ctk = CTkImage(light_image=Image.open(r"C:\Users\Olya\PycharmProjects\myFirstProject\img\bg.png"),
                           size=(450, 400))
        self.img_label = CTkLabel(self.left_frame, text='Welcome', image=img_ctk, font=('Helvetica', 60, 'bold'))
        self.img_label.pack()


        main_font = ('Helvetica', 20, 'bold')
        self.right_frame = CTkFrame(self, fg_color='white')
        self.right_frame.pack_propagate(False)
        self.right_frame.pack(side='right', fill='both', expand=True)


        CTkLabel(self.right_frame, text='LogiTalk', font=main_font, text_color='#6753cc').pack(pady=20)


        self.name_entry = CTkEntry(self.right_frame, placeholder_text='☻ ім`я',
                                   height=45, font=main_font, corner_radius=25, fg_color='#eae6ff', border_color='#eae6ff',
                                   text_color='#6753cc', placeholder_text_color='#6753cc')
        self.name_entry.pack(fill='x', padx=10)


        self.avatar_btn = CTkButton(self.right_frame, text="Обрати аватар", height=35, command=self.choose_avatar)
        self.avatar_btn.pack(pady=10)


        self.connect_button = CTkButton(self.right_frame, text='УВІЙТИ', height=45,
                                        corner_radius=25, fg_color='#d06fc0', font=main_font, text_color='white',
                                        command=self.open_chat)
        self.connect_button.pack(fill='x', padx=50, pady=10)


    def choose_avatar(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if path:
            self.avatar_path = path


    def open_chat(self):
        username = self.name_entry.get().strip()
        if not username:
            username = "Гість"
        self.destroy()
        chat = MainWindow(username, self.avatar_path)
        chat.mainloop()




if __name__ == "__main__":
    app = AuthWindow()
    app.mainloop()