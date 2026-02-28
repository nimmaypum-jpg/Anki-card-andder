import customtkinter
import tkinter as tk

try:
    print("Starting GUI test...")
    root = customtkinter.CTk()
    root.title("Test Window")
    root.geometry("300x200")
    label = customtkinter.CTkLabel(root, text="If you see this, GUI works!")
    label.pack(pady=20)
    print("Window created. Closing in 3 seconds...")
    root.after(3000, root.destroy)
    root.mainloop()
    print("Test finished successfully.")
except Exception as e:
    print(f"GUI Error: {e}")
