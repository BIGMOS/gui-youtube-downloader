"""Simple YouTube downloader GUI around yt-dlp. Double-click to run."""
import glob
import os
import queue
import re
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

FORMATS = {
    "Best quality (MP4)": "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b",
    "Plays everywhere (H.264 MP4)": "bv*[vcodec^=avc1]+ba[ext=m4a]/b[ext=mp4]/b",
    "Audio only (M4A)": "ba[ext=m4a]/ba",
}

PROGRESS_RE = re.compile(r"\[download\]\s+([\d.]+)%")


def find_yt_dlp():
    path = shutil.which("yt-dlp")
    if path:
        return path
    candidate = os.path.expandvars(r"%APPDATA%\Python\Python311\Scripts\yt-dlp.exe")
    return candidate if os.path.exists(candidate) else None


def find_ffmpeg_dir():
    path = shutil.which("ffmpeg")
    if path:
        return os.path.dirname(path)
    pattern = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe"
    )
    matches = glob.glob(pattern)
    return os.path.dirname(matches[0]) if matches else None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader")
        self.geometry("640x420")
        self.minsize(480, 340)

        self.yt_dlp = find_yt_dlp()
        self.ffmpeg_dir = find_ffmpeg_dir()
        self.proc = None
        self.cancelled = False
        self.lines = queue.Queue()

        pad = {"padx": 10, "pady": 4}
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=8, pady=8)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="Video link:").grid(row=0, column=0, sticky="w", **pad)
        self.url = tk.StringVar()
        url_entry = ttk.Entry(frm, textvariable=self.url)
        url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", **pad)
        url_entry.focus()
        url_entry.bind("<Return>", lambda e: self.start())
        ttk.Button(frm, text="Paste", command=self.paste).grid(row=0, column=3, **pad)

        ttk.Label(frm, text="Save to:").grid(row=1, column=0, sticky="w", **pad)
        self.folder = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        ttk.Entry(frm, textvariable=self.folder).grid(row=1, column=1, columnspan=2, sticky="ew", **pad)
        ttk.Button(frm, text="Browse...", command=self.browse).grid(row=1, column=3, **pad)

        ttk.Label(frm, text="Format:").grid(row=2, column=0, sticky="w", **pad)
        self.fmt = tk.StringVar(value=next(iter(FORMATS)))
        ttk.Combobox(frm, textvariable=self.fmt, values=list(FORMATS), state="readonly").grid(
            row=2, column=1, sticky="w", **pad
        )

        self.dl_btn = ttk.Button(frm, text="Download", command=self.start)
        self.dl_btn.grid(row=2, column=2, sticky="e", **pad)
        self.cancel_btn = ttk.Button(frm, text="Cancel", command=self.cancel, state="disabled")
        self.cancel_btn.grid(row=2, column=3, **pad)

        self.progress = ttk.Progressbar(frm, maximum=100)
        self.progress.grid(row=3, column=0, columnspan=4, sticky="ew", **pad)
        self.status = tk.StringVar(value="Paste a link and click Download.")
        ttk.Label(frm, textvariable=self.status).grid(row=4, column=0, columnspan=4, sticky="w", **pad)

        self.log = tk.Text(frm, height=10, wrap="word", state="disabled", font=("Consolas", 9))
        self.log.grid(row=5, column=0, columnspan=4, sticky="nsew", **pad)
        frm.rowconfigure(5, weight=1)

        if not self.yt_dlp:
            self.status.set("yt-dlp not found. Install it with:  pip install --user yt-dlp")
            self.dl_btn.config(state="disabled")
        elif not self.ffmpeg_dir:
            self.write_log("Warning: ffmpeg not found, video and audio may download as separate files.\n")

        self.after(100, self.poll)

    def paste(self):
        try:
            self.url.set(self.clipboard_get().strip())
        except tk.TclError:
            pass

    def browse(self):
        d = filedialog.askdirectory(initialdir=self.folder.get())
        if d:
            self.folder.set(d)

    def write_log(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.config(state="disabled")

    def start(self):
        url = self.url.get().strip()
        if not url:
            messagebox.showwarning("No link", "Paste a YouTube link first.")
            return
        if self.proc:
            return
        fmt_name = self.fmt.get()
        cmd = [self.yt_dlp, "-f", FORMATS[fmt_name], "--no-playlist", "--newline",
               "-P", self.folder.get()]
        if fmt_name != "Audio only (M4A)":
            cmd += ["--merge-output-format", "mp4"]
        if self.ffmpeg_dir:
            cmd += ["--ffmpeg-location", self.ffmpeg_dir]
        cmd.append(url)

        self.progress["value"] = 0
        self.status.set("Starting...")
        self.dl_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.write_log(f"\n--- {url}\n")
        threading.Thread(target=self.run, args=(cmd,), daemon=True).start()

    def run(self, cmd):
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for line in self.proc.stdout:
                self.lines.put(line)
            code = self.proc.wait()
        except Exception as e:
            self.lines.put(f"Error: {e}\n")
            code = -1
        self.lines.put(("DONE", code))

    def poll(self):
        try:
            while True:
                item = self.lines.get_nowait()
                if isinstance(item, tuple):
                    self.finish(item[1])
                    continue
                m = PROGRESS_RE.search(item)
                if m:
                    pct = float(m.group(1))
                    self.progress["value"] = pct
                    self.status.set(item.replace("[download]", "").strip())
                else:
                    self.write_log(item)
                    if "Merging" in item:
                        self.status.set("Combining video and audio...")
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def finish(self, code):
        self.proc = None
        self.dl_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        if code == 0:
            self.progress["value"] = 100
            self.status.set(f"Done! Saved to {self.folder.get()}")
            self.url.set("")
        elif self.cancelled:
            self.status.set("Cancelled.")
        else:
            self.status.set("Download failed - see the log below.")
        self.cancelled = False

    def cancel(self):
        if self.proc:
            self.cancelled = True
            self.proc.kill()


if __name__ == "__main__":
    App().mainloop()
