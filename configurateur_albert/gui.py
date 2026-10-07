"""Interface graphique (Tkinter) : un assistant pas à pas pour novices."""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import font as tkfont
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from . import APP_NAME, __version__, albert, installer, paths, texts
from .installer import Plan

PAD = 12

# Symboles simples et colorés : les émojis s'affichent mal dans Tk (surtout sous Windows).
ICONS = {"ok": ("✔", "#18753c"), "erreur": ("✖", "#ce0500"), "attention": ("!", "#b34000"),
         "ignoré": ("–", "#666666"), "en cours": ("…", "#000091"), "": ("·", "#666666")}


class QueueReporter:
    """Les étapes tournent dans un fil d'exécution séparé : on passe par une file."""

    def __init__(self, q: queue.Queue):
        self.q = q

    def log(self, message: str) -> None:
        self.q.put(("log", message))

    def step(self, step_id: str, status: str, detail: str = "") -> None:
        self.q.put(("step", (step_id, status, detail)))


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {__version__}")
        self.geometry("820x620")
        self.minsize(720, 540)
        style = ttk.Style(self)
        if sys.platform.startswith("linux"):
            style.theme_use("clam")
        base = tkfont.nametofont("TkDefaultFont")
        self.font_title = base.copy()
        self.font_title.configure(size=max(base.cget("size"), 10) + 6, weight="bold")
        self.font_icon = base.copy()
        self.font_icon.configure(weight="bold")
        style.configure("Title.TLabel", font=self.font_title)
        style.configure("Small.TLabel", foreground="#555")

        self.q: queue.Queue = queue.Queue()
        self.diag: installer.Diagnostic | None = None
        self.key: str | None = None
        self.models: list[albert.Model] = []
        cat = paths.catalog()
        self.var_opencode = tk.BooleanVar(value=True)
        self.var_pi = tk.BooleanVar(value=True)
        self.var_vscode = tk.BooleanVar(value=False)
        self.var_tests = tk.BooleanVar(value=True)
        self.var_model = tk.StringVar()
        self.skill_vars = {s["id"]: tk.BooleanVar(value=s.get("default", False)) for s in cat["skills"]}
        self.mcp_vars = {m["id"]: tk.BooleanVar(value=m.get("default", False)) for m in cat["mcp"]}
        self.results: dict[str, str] = {}

        self.header = ttk.Label(self, style="Title.TLabel")
        self.header.pack(fill="x", padx=PAD, pady=(PAD, 4))
        ttk.Separator(self).pack(fill="x")
        self.body = ttk.Frame(self, padding=PAD)
        self.body.pack(fill="both", expand=True)
        ttk.Separator(self).pack(fill="x")
        footer = ttk.Frame(self, padding=(PAD, 8))
        footer.pack(fill="x")
        self.btn_back = ttk.Button(footer, text="◀ Retour", command=self.back)
        self.btn_back.pack(side="left")
        self.btn_next = ttk.Button(footer, text="Suivant ▶", command=self.next)
        self.btn_next.pack(side="right")
        self.step_label = ttk.Label(footer, style="Small.TLabel")
        self.step_label.pack(side="right", padx=PAD)

        self.pages = [self.page_welcome, self.page_diag, self.page_key, self.page_tools,
                      self.page_skills, self.page_mcp, self.page_recap, self.page_install, self.page_done]
        self.index = 0
        self.show()
        self.after(100, self.poll)

    # --- navigation -----------------------------------------------------------

    def show(self) -> None:
        for w in self.body.winfo_children():
            w.destroy()
        self.btn_back.state(["!disabled"] if 0 < self.index < 7 else ["disabled"])
        self.btn_next.configure(text="Suivant ▶")
        self.btn_next.state(["!disabled"])
        self.step_label.configure(text=f"Étape {self.index + 1} / {len(self.pages)}")
        self.pages[self.index]()

    def next(self) -> None:
        if self.index == len(self.pages) - 1:
            self.destroy()
            return
        validator = getattr(self, f"validate_{self.index}", None)
        if validator and not validator():
            return
        self.index += 1
        self.show()

    def back(self) -> None:
        if self.index > 0:
            self.index -= 1
            self.show()

    def text_block(self, parent, content: str, height: int | None = None) -> None:
        lbl = ttk.Label(parent, text=content, justify="left", wraplength=760)
        lbl.pack(anchor="w", fill="x", pady=(0, 8))

    def run_bg(self, func, done) -> None:
        """Lance func() en arrière-plan ; done(résultat, erreur) dans l'interface."""
        def worker():
            try:
                res = func()
                self.q.put(("call", (done, res, None)))
            except Exception as e:  # noqa: BLE001
                self.q.put(("call", (done, None, e)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self) -> None:
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "call":
                    done, res, err = payload
                    done(res, err)
                elif kind == "log" and hasattr(self, "log_widget") and self.log_widget.winfo_exists():
                    self.log_widget.configure(state="normal")
                    self.log_widget.insert("end", payload + "\n")
                    self.log_widget.see("end")
                    self.log_widget.configure(state="disabled")
                elif kind == "step":
                    self.update_step(*payload)
        except queue.Empty:
            pass
        self.after(100, self.poll)

    # --- pages ----------------------------------------------------------------

    def page_welcome(self) -> None:
        self.header.configure(text="Bienvenue")
        self.text_block(self.body, texts.WELCOME)
        ttk.Button(self.body, text="Désinstaller (retirer les réglages Albert)…",
                   command=self.open_uninstall).pack(anchor="w", side="bottom")

    def page_diag(self) -> None:
        self.header.configure(text="Diagnostic de votre ordinateur")
        self.diag_frame = ttk.Frame(self.body)
        self.diag_frame.pack(fill="both", expand=True)
        ttk.Label(self.diag_frame, text="Analyse en cours…").pack(anchor="w")
        self.btn_next.state(["disabled"])
        self.run_bg(installer.diagnose, self.diag_done)

    def diag_done(self, d, err) -> None:
        if self.index != 1:
            return
        for w in self.diag_frame.winfo_children():
            w.destroy()
        if err:
            ttk.Label(self.diag_frame, text=f"Erreur pendant le diagnostic : {err}").pack(anchor="w")
            self.btn_next.state(["!disabled"])
            return
        self.diag = d
        rows = [("Système", d.os, "ok")]
        if d.node:
            rows.append(("Node.js", d.node + ("" if d.node_ok_for_pi else " (trop ancien pour Pi : une copie récente sera installée)"),
                         "ok" if d.node_ok_for_pi else "attention"))
        else:
            rows.append(("Node.js", "absent : il sera installé dans votre dossier personnel", "attention"))
        if paths.IS_WINDOWS:
            rows.append(("Git for Windows", d.git_bash or "absent : nécessaire à Pi, l'application tentera de l'installer",
                         "ok" if d.git_bash else "attention"))
        oc_note = d.opencode or "absent : sera installé"
        if d.opencode_major and d.opencode_major != 1:
            oc_note += " (version 2 : la version 1, testée, sera installée)"
        rows.append(("OpenCode", oc_note, "ok" if d.opencode_major == 1 else "attention"))
        rows.append(("Pi", d.pi or "absent : sera installé", "ok" if d.pi else "attention"))
        rows.append(("Clé Albert", f"déjà enregistrée ({albert.mask(d.key)})" if d.key else "pas encore enregistrée",
                     "ok" if d.key else "attention"))
        rows.append(("VS Code", "présent" if d.vscode else "absent (facultatif)", "ok" if d.vscode else ""))
        grid = ttk.Frame(self.diag_frame)
        grid.pack(anchor="w")
        for r, (name, value, status) in enumerate(rows):
            sym, color = ICONS.get(status, ICONS[""])
            ttk.Label(grid, text=sym, foreground=color, font=self.font_icon, width=2).grid(
                row=r, column=0, sticky="w", pady=3)
            ttk.Label(grid, text=name, width=18).grid(row=r, column=1, sticky="w")
            ttk.Label(grid, text=value, wraplength=560).grid(row=r, column=2, sticky="w")
        ttk.Label(self.diag_frame, text="\n« ! » n'est pas une erreur : l'application s'en occupe.",
                  style="Small.TLabel").pack(anchor="w")
        self.btn_next.state(["!disabled"])

    def page_key(self) -> None:
        self.header.configure(text="Votre clé Albert API")
        self.text_block(self.body, texts.KEY_HELP)
        ttk.Button(self.body, text="Ouvrir la page des clés",
                   command=lambda: webbrowser.open(paths.catalog()["albert"]["keys_url"])).pack(anchor="w", pady=(0, 10))
        existing = self.diag.key if self.diag else None
        self.var_key_mode = tk.StringVar(value="existing" if existing else "new")
        if existing:
            ttk.Radiobutton(self.body, text=f"Utiliser la clé déjà enregistrée ({albert.mask(existing)})",
                            variable=self.var_key_mode, value="existing").pack(anchor="w")
            ttk.Radiobutton(self.body, text="Utiliser une nouvelle clé :", variable=self.var_key_mode,
                            value="new").pack(anchor="w")
        row = ttk.Frame(self.body)
        row.pack(fill="x", pady=6)
        self.entry_key = ttk.Entry(row, show="•", width=60)
        self.entry_key.pack(side="left", fill="x", expand=True)
        self.entry_key.bind("<FocusIn>", lambda e: self.var_key_mode.set("new"))
        ttk.Button(row, text="Tester la clé", command=self.test_key).pack(side="left", padx=6)
        self.key_status = ttk.Label(self.body, text="", wraplength=760)
        self.key_status.pack(anchor="w", pady=6)
        if self.key and self.models:
            self.key_status.configure(text=f"✔ Clé valide ({albert.mask(self.key)}), "
                                           f"{len(self.models)} modèle(s) disponible(s).", foreground=ICONS["ok"][1])

    def test_key(self) -> None:
        if self.var_key_mode.get() == "existing" and self.diag and self.diag.key:
            key = self.diag.key
        else:
            key = albert.normalize_key(self.entry_key.get())
        err = albert.check_key_format(key)
        if err:
            self.key_status.configure(text="✖ " + err, foreground=ICONS["erreur"][1])
            return
        self.key_status.configure(text="Test en cours…", foreground="")

        def done(models, e):
            if self.index != 2:
                return
            if e:
                self.key, self.models = None, []
                self.key_status.configure(text="✖ " + str(e), foreground=ICONS["erreur"][1])
            elif not models:
                self.key_status.configure(text="✖ Aucun modèle de conversation n'est disponible avec cette clé.",
                                          foreground=ICONS["erreur"][1])
            else:
                self.key, self.models = key, models
                self.entry_key.delete(0, "end")
                self.key_status.configure(text=f"✔ Clé valide ({albert.mask(key)}), "
                                               f"{len(models)} modèle(s) disponible(s). Cliquez sur « Suivant ».",
                                          foreground=ICONS["ok"][1])
        self.run_bg(lambda: albert.usable_models(albert.list_raw(key)), done)

    def validate_2(self) -> bool:
        if not (self.key and self.models):
            messagebox.showinfo(APP_NAME, "Testez d'abord votre clé (bouton « Tester la clé »).")
            return False
        return True

    def page_tools(self) -> None:
        self.header.configure(text="Assistants et modèle")
        d = self.diag
        ttk.Label(self.body, text="Quels assistants voulez-vous ?").pack(anchor="w")
        ttk.Checkbutton(self.body, text="OpenCode — interface en terminal, extension VS Code"
                        + (f" (installé : {d.opencode})" if d and d.opencode else ""),
                        variable=self.var_opencode).pack(anchor="w", pady=2)
        ttk.Checkbutton(self.body, text="Pi — plus léger, sait faire de l'OCR d'images"
                        + (f" (installé : {d.pi})" if d and d.pi else ""),
                        variable=self.var_pi).pack(anchor="w", pady=2)
        ttk.Label(self.body, text="\nModèle utilisé par défaut (modifiable ensuite dans l'assistant) :").pack(anchor="w")
        labels = [f"{m.id} — {m.label}" for m in self.models]
        combo = ttk.Combobox(self.body, values=labels, state="readonly", width=90)
        default = self.var_model.get() or albert.default_model_id(self.models)
        for i, m in enumerate(self.models):
            if m.id == default:
                combo.current(i)
        combo.bind("<<ComboboxSelected>>", lambda e: self.var_model.set(self.models[combo.current()].id))
        self.var_model.set(default or "")
        combo.pack(anchor="w", pady=4)
        ttk.Label(self.body, text="Tous les modèles disponibles seront déclarés ; seul le choix par défaut change.",
                  style="Small.TLabel").pack(anchor="w")
        ttk.Label(self.body, text="").pack()
        cb = ttk.Checkbutton(self.body, text="Installer l'extension OpenCode pour VS Code",
                             variable=self.var_vscode)
        cb.pack(anchor="w")
        if not (d and d.vscode):
            cb.state(["disabled"])
            self.var_vscode.set(False)
        ttk.Checkbutton(self.body, text="Vérifier à la fin que tout fonctionne (environ 1 à 2 minutes)",
                        variable=self.var_tests).pack(anchor="w", pady=2)

    def validate_3(self) -> bool:
        if not (self.var_opencode.get() or self.var_pi.get()):
            messagebox.showinfo(APP_NAME, "Choisissez au moins un assistant.")
            return False
        return True

    def checklist(self, items: list[dict], variables: dict) -> None:
        canvas = tk.Canvas(self.body, highlightthickness=0)
        scroll = ttk.Scrollbar(self.body, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Molette de la souris (Tk ne la relie pas tout seul à un Canvas).
        def wheel(event) -> None:
            if getattr(event, "num", None) == 4:
                step = -1
            elif getattr(event, "num", None) == 5:
                step = 1
            else:
                step = -1 if event.delta > 0 else 1
            canvas.yview_scroll(step, "units")

        def bind_wheel(_e=None) -> None:
            canvas.bind_all("<MouseWheel>", wheel)      # Windows, macOS
            canvas.bind_all("<Button-4>", wheel)        # Linux
            canvas.bind_all("<Button-5>", wheel)

        def unbind_wheel(_e=None) -> None:
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                canvas.unbind_all(seq)

        canvas.bind("<Enter>", bind_wheel)
        canvas.bind("<Leave>", unbind_wheel)
        canvas.bind("<Destroy>", unbind_wheel)
        for item in items:
            ttk.Checkbutton(inner, text=item["name"], variable=variables[item["id"]]).pack(anchor="w", pady=(6, 0))
            ttk.Label(inner, text=item["description"], wraplength=700,
                      style="Small.TLabel").pack(anchor="w", padx=(24, 0))

    def page_skills(self) -> None:
        self.header.configure(text="Skills (savoir-faire)")
        self.text_block(self.body, "Un skill est un mode d'emploi que l'assistant consulte quand la tâche "
                                   "s'y prête (ex. « transcris cours.mp3 »). Ils sont installés dans "
                                   f"{paths.skills_dir()}, lu par OpenCode et par Pi.")
        self.checklist(paths.catalog()["skills"], self.skill_vars)

    def page_mcp(self) -> None:
        self.header.configure(text="Connecteurs (MCP)")
        self.text_block(self.body, "Un MCP branche l'assistant sur un service extérieur. " + texts.MCP_WARNING)
        self.checklist(paths.catalog()["mcp"], self.mcp_vars)

    def build_plan(self) -> Plan:
        return Plan(
            key=self.key or "", models=self.models,
            default_model=self.var_model.get() or albert.default_model_id(self.models) or self.models[0].id,
            opencode=self.var_opencode.get(), pi=self.var_pi.get(),
            skills=[k for k, v in self.skill_vars.items() if v.get()],
            mcp=[k for k, v in self.mcp_vars.items() if v.get()],
            vscode=self.var_vscode.get(), run_tests=self.var_tests.get(),
        )

    def page_recap(self) -> None:
        self.header.configure(text="Récapitulatif")
        p = self.build_plan()
        cat = paths.catalog()
        names = lambda kind, ids: ", ".join(i["name"] for i in cat[kind] if i["id"] in ids) or "aucun"
        tools = " et ".join(t for t, on in (("OpenCode", p.opencode), ("Pi", p.pi)) if on)
        lines = [
            f"• Assistant(s) : {tools}",
            f"• Modèle par défaut : {p.default_model}",
            f"• Clé : {albert.mask(p.key)} (rangée dans le coffre de ce poste)",
            f"• Skills : {names('skills', p.skills)}",
            f"• Connecteurs : {names('mcp', p.mcp)}",
            f"• Extension VS Code : {'oui' if p.vscode else 'non'}",
            "",
            "Vos réglages existants sont conservés ; chaque fichier modifié est d'abord",
            "sauvegardé (copie .bak datée). Durée : quelques minutes selon la connexion.",
        ]
        self.text_block(self.body, "\n".join(lines))
        self.btn_next.configure(text="Installer ▶")

    def page_install(self) -> None:
        self.header.configure(text="Installation en cours…")
        self.btn_next.state(["disabled"])
        steps = ttk.Frame(self.body)
        steps.pack(fill="x")
        self.step_widgets = {}
        for r, (sid, label) in enumerate(installer.STEPS):
            icon = ttk.Label(steps, text="·", width=3, font=self.font_icon)
            icon.grid(row=r, column=0, sticky="w")
            ttk.Label(steps, text=label, width=32).grid(row=r, column=1, sticky="w")
            detail = ttk.Label(steps, text="", style="Small.TLabel", wraplength=470)
            detail.grid(row=r, column=2, sticky="w")
            self.step_widgets[sid] = (icon, detail)
        ttk.Label(self.body, text="Journal détaillé :").pack(anchor="w", pady=(10, 0))
        self.log_widget = ScrolledText(self.body, height=10, state="disabled", font="TkFixedFont")
        self.log_widget.pack(fill="both", expand=True)
        plan = self.build_plan()

        def done(results, err):
            self.results = results or {}
            if err:
                QueueReporter(self.q).log(f"Erreur inattendue : {err}")
                self.results["erreur"] = "erreur"
            self.header.configure(text="Installation terminée")
            self.btn_next.configure(text="Continuer ▶")
            self.btn_next.state(["!disabled"])
        self.run_bg(lambda: installer.run_plan(plan, QueueReporter(self.q)), done)

    def update_step(self, sid: str, status: str, detail: str) -> None:
        if not hasattr(self, "step_widgets") or sid not in self.step_widgets:
            return
        icon, lbl = self.step_widgets[sid]
        if icon.winfo_exists():
            sym, color = ICONS.get(status, ICONS[""])
            icon.configure(text=sym, foreground=color)
            lbl.configure(text=detail)

    def page_done(self) -> None:
        failed = [s for s in self.results.values() if s in ("erreur", "attention")]
        self.header.configure(text="C'est prêt !" if not failed else "Terminé, avec des points à vérifier")
        self.btn_next.configure(text="Fermer")
        self.text_block(self.body, texts.USAGE)
        if failed:
            ttk.Label(self.body, text="En cas de souci :", font=self.font_icon).pack(anchor="w")
            for symptom, fix in texts.TROUBLESHOOTING:
                ttk.Label(self.body, text=f"• {symptom} : {fix}", wraplength=760,
                          style="Small.TLabel").pack(anchor="w")

    # --- désinstallation ------------------------------------------------------

    def open_uninstall(self) -> None:
        win = tk.Toplevel(self)
        win.title("Désinstaller")
        win.geometry("640x420")
        frame = ttk.Frame(win, padding=PAD)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Retire les réglages Albert d'OpenCode et de Pi, les skills installés et le "
                              "chargement automatique de la clé. Vos autres réglages sont conservés.",
                  wraplength=600).pack(anchor="w")
        v_key = tk.BooleanVar(value=True)
        v_tools = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Supprimer aussi la clé Albert de ce poste", variable=v_key).pack(anchor="w", pady=2)
        ttk.Checkbutton(frame, text="Désinstaller aussi OpenCode et Pi", variable=v_tools).pack(anchor="w", pady=2)
        log = ScrolledText(frame, height=10, state="disabled")
        q2: queue.Queue = queue.Queue()

        class R:
            def log(self, m):
                q2.put(m)

            def step(self, *a):
                pass

        def pump():
            try:
                while True:
                    m = q2.get_nowait()
                    log.configure(state="normal")
                    log.insert("end", m + "\n")
                    log.configure(state="disabled")
            except queue.Empty:
                pass
            if win.winfo_exists():
                win.after(100, pump)

        def go():
            if not messagebox.askyesno("Désinstaller", "Confirmer la désinstallation ?", parent=win):
                return
            btn.state(["disabled"])
            threading.Thread(target=lambda: installer.uninstall(R(), remove_key=v_key.get(),
                                                                remove_tools=v_tools.get()),
                             daemon=True).start()
        btn = ttk.Button(frame, text="Désinstaller", command=go)
        btn.pack(anchor="w", pady=6)
        log.pack(fill="both", expand=True)
        pump()


def run() -> int:
    if sys.platform == "win32":
        try:  # texte net sur les écrans haute résolution
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass
    app = App()
    # Lancée depuis un terminal (macOS surtout), la fenêtre s'ouvrirait derrière lui.
    app.lift()
    app.attributes("-topmost", True)
    app.after(800, lambda: app.attributes("-topmost", False))
    app.focus_force()
    app.mainloop()
    return 0
