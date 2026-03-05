import json
import threading
import traceback
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, VERTICAL, W, Button, Entry, Frame, Label, OptionMenu, Scrollbar, StringVar, Text, Tk, filedialog, messagebox

from fcgen import PROJECT_ROOT, TEMPLATES_DIR
from fcgen.core.runner import run_template


TEMPLATES = {
    "bracket": TEMPLATES_DIR / "bracket" / "examples" / "basic.json",
    "enclosure": TEMPLATES_DIR / "enclosure" / "examples" / "basic.json",
    "adapter_plate": TEMPLATES_DIR / "adapter_plate" / "examples" / "basic.json",
}
DEFAULT_OUT = {
    "bracket": "output/bracket",
    "enclosure": "output/enclosure",
    "adapter_plate": "output/adapter_plate",
}


class FcgenUI:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("fcgen UI")
        self.template_var = StringVar(value="bracket")
        self.out_dir_var = StringVar(value=str((PROJECT_ROOT / DEFAULT_OUT["bracket"]).resolve()))

        top = Frame(root)
        top.pack(fill="x", padx=10, pady=8)

        Label(top, text="Template").grid(row=0, column=0, sticky=W)
        OptionMenu(top, self.template_var, *TEMPLATES.keys(), command=self.on_template_change).grid(row=0, column=1, sticky=W)

        Label(top, text="Output Dir").grid(row=1, column=0, sticky=W)
        self.out_entry = Entry(top, textvariable=self.out_dir_var, width=70)
        self.out_entry.grid(row=1, column=1, sticky=W)
        Button(top, text="Browse", command=self.pick_output_dir).grid(row=1, column=2, padx=6)

        mid = Frame(root)
        mid.pack(fill=BOTH, expand=True, padx=10, pady=4)
        Label(mid, text="Params JSON").pack(anchor=W)

        text_frame = Frame(mid)
        text_frame.pack(fill=BOTH, expand=True)
        self.params_text = Text(text_frame, height=20, width=110)
        self.params_text.pack(side=LEFT, fill=BOTH, expand=True)
        sb = Scrollbar(text_frame, orient=VERTICAL, command=self.params_text.yview)
        sb.pack(side=RIGHT, fill="y")
        self.params_text.configure(yscrollcommand=sb.set)

        btns = Frame(root)
        btns.pack(fill="x", padx=10, pady=8)
        Button(btns, text="Load Example", command=self.load_example).pack(side=LEFT)
        Button(btns, text="Open JSON", command=self.open_json).pack(side=LEFT, padx=6)
        Button(btns, text="Save JSON As...", command=self.save_json_as).pack(side=LEFT)
        Button(btns, text="Run", command=self.run_clicked).pack(side=LEFT, padx=12)

        log_frame = Frame(root)
        log_frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        Label(log_frame, text="Result").pack(anchor=W)
        self.log_text = Text(log_frame, height=10, width=110)
        self.log_text.pack(fill=BOTH, expand=True)

        self.load_example()

    def on_template_change(self, _: str) -> None:
        tpl = self.template_var.get()
        self.out_dir_var.set(str((PROJECT_ROOT / DEFAULT_OUT[tpl]).resolve()))
        self.load_example()

    def load_example(self) -> None:
        p = TEMPLATES[self.template_var.get()]
        self.params_text.delete("1.0", END)
        self.params_text.insert("1.0", p.read_text(encoding="utf-8"))
        self.log("Loaded example: " + str(p))

    def open_json(self) -> None:
        path = filedialog.askopenfilename(
            title="Open params JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(PROJECT_ROOT),
        )
        if not path:
            return
        self.params_text.delete("1.0", END)
        self.params_text.insert("1.0", Path(path).read_text(encoding="utf-8"))
        self.log("Opened: " + path)

    def save_json_as(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save params JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialdir=str(PROJECT_ROOT),
        )
        if not path:
            return
        Path(path).write_text(self.params_text.get("1.0", END), encoding="utf-8")
        self.log("Saved: " + path)

    def pick_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Select output directory", initialdir=str(PROJECT_ROOT))
        if path:
            self.out_dir_var.set(path)

    def run_clicked(self) -> None:
        t = threading.Thread(target=self._run_worker, daemon=True)
        t.start()

    def _run_worker(self) -> None:
        try:
            template = self.template_var.get()
            params_text = self.params_text.get("1.0", END).strip()
            params = json.loads(params_text)
            out_dir = Path(self.out_dir_var.get()).resolve()
            self.log(f"Running template={template} out={out_dir}")
            result = run_template(template=template, params=params, out_dir=out_dir, dry_run=False)
            self.log(json.dumps(result, indent=2))
            self.log(f"Done. STEP: {result['outputs']['step']}")
        except Exception as exc:
            self.log("ERROR: " + str(exc))
            self.log(traceback.format_exc())
            messagebox.showerror("fcgen error", str(exc))

    def log(self, msg: str) -> None:
        self.log_text.insert(END, msg + "\n")
        self.log_text.see(END)


def main() -> None:
    root = Tk()
    app = FcgenUI(root)
    _ = app
    root.mainloop()


if __name__ == "__main__":
    main()
