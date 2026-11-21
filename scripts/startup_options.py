"""Read the citation standard, output mode, and models from the local audit dialog."""

import argparse
import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from urllib.parse import urlsplit

from audit_ui import bind_paste, blue_dialog, paste_into
from cross_ai import DEFAULT_MODELS, configured_credentials, load_bundle, prepared_bundle, run_reviews


MODEL_CHOICES = {
    "codex": "仅 Codex",
    "deepseek": "DeepSeek + Codex",
}
DEEPSEEK_EVIDENCE_SCOPE = "bibliography_evidence"
STANDARD_CHOICES = {"journal": "目标期刊", "gbt2015": "GB/T 7714-2015"}
LAYOUT_CHOICES = {
    "latex": "是，生成 BibTeX (.bib)",
    "text": "否，生成纯文本 (.txt)",
}


def journal_guide_url(value):
    url = value.strip()
    if url and "://" not in url:
        url = "https://" + url
    parts = urlsplit(url)
    if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.username is not None
            or any(character.isspace() for character in url)):
        raise ValueError("请输入有效的期刊官网或作者指南网址。")
    return url


def choose_settings(ai="codex", standard="", journal_url="", layout="", captured_credentials=None):
    window, frame = blue_dialog("Scholarly Citation Audit", "审查设置", lab_logo=True)
    frame.columnconfigure(1, weight=1)
    selected_standard = tk.StringVar(value=standard or ("journal" if journal_url else ""))
    selected_layout = tk.StringVar(value=layout)
    selected_ai = tk.StringVar(value=ai)
    message = tk.StringVar(value="")

    ttk.Label(frame, text="1  审查与著录规范", style="Section.TLabel").grid(row=1, column=0, columnspan=2, sticky="w")
    standard_buttons = ttk.Frame(frame)
    standard_buttons.grid(row=2, column=0, columnspan=2, sticky="w", pady=("3p", "5p"))
    for code, label in STANDARD_CHOICES.items():
        ttk.Radiobutton(standard_buttons, text=label, value=code, variable=selected_standard).pack(
            side="left", padx=(0, "14p"))
    ttk.Label(frame, text="期刊网址").grid(row=3, column=0, sticky="w", padx=(0, "7p"))
    url_controls = ttk.Frame(frame)
    url_controls.grid(row=3, column=1, sticky="ew")
    journal = ttk.Entry(url_controls, width=46)
    journal.insert(0, journal_url)
    journal.pack(side="left", fill="x", expand=True)

    def empty_clipboard():
        message.set("剪贴板暂无可粘贴的文本，可直接输入网址。")

    def paste_journal():
        selected_standard.set("journal")
        paste_into(journal, empty_clipboard)

    ttk.Button(url_controls, text="粘贴", command=paste_journal, width=5).pack(side="left", padx=("5p", 0))
    bind_paste(journal, empty_clipboard)
    journal_hint = tk.StringVar()
    ttk.Label(frame, textvariable=journal_hint, style="Hint.TLabel").grid(
        row=4, column=1, sticky="w", pady=("3p", 0))

    def update_journal(*_):
        enabled = selected_standard.get() == "journal"
        journal.state(["!disabled"] if enabled else ["disabled"])
        journal_hint.set("填写期刊官网或作者指南网址。" if enabled else "选择目标期刊后填写网址。")
        if enabled:
            journal.focus_set()

    selected_standard.trace_add("write", update_journal)
    update_journal()

    ttk.Label(frame, text="2  是否用于 LaTeX 排版", style="Section.TLabel").grid(
        row=5, column=0, columnspan=2, sticky="w", pady=("10p", 0))
    layout_buttons = ttk.Frame(frame)
    layout_buttons.grid(row=6, column=0, columnspan=2, sticky="w", pady=("4p", 0))
    for code, label in LAYOUT_CHOICES.items():
        ttk.Radiobutton(layout_buttons, text=label, value=code, variable=selected_layout).pack(
            side="left", padx=(0, "14p"))

    ttk.Label(frame, text="3  参与核验的模型", style="Section.TLabel").grid(
        row=7, column=0, columnspan=2, sticky="w", pady=("10p", 0))
    model_buttons = ttk.Frame(frame)
    model_buttons.grid(row=8, column=0, columnspan=2, sticky="w", pady=("4p", 0))
    for code, label in MODEL_CHOICES.items():
        ttk.Radiobutton(model_buttons, text=label, value=code, variable=selected_ai).pack(
            side="left", padx=(0, "14p"))

    api_panel = ttk.Frame(frame)
    api_panel.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    api_panel.columnconfigure(1, weight=1)
    configured_key, configured_model = configured_credentials("deepseek")
    ttk.Label(api_panel, text="DeepSeek API 密钥").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=2)
    key = ttk.Entry(api_panel, show="*", width=34)
    key.grid(row=0, column=1, sticky="ew", pady=2)
    key.bind("<<Copy>>", lambda event: "break")
    key.bind("<<Cut>>", lambda event: "break")
    bind_paste(key, empty_clipboard)
    ttk.Label(api_panel, text="DeepSeek 模型").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=2)
    model_entry = ttk.Entry(api_panel, width=34)
    model_entry.insert(0, configured_model or DEFAULT_MODELS["deepseek"])
    model_entry.grid(row=1, column=1, sticky="ew", pady=2)
    ttk.Label(
        api_panel,
        text=("本次将向 DeepSeek 发送公开书目信息、公开出版记录与著录规范的必要节选。"
              "稿件正文和附件保留在本地。"),
        style="Hint.TLabel", justify="left", wraplength="310p",
    ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(7, 0))
    ttk.Label(frame, textvariable=message, style="Hint.TLabel").grid(
        row=10, column=0, columnspan=2, sticky="w", pady=(5, 0))
    result = None

    def submit(event=None):
        nonlocal result
        choice = selected_standard.get()
        if not choice:
            message.set("请选择目标期刊或 GB/T 7714-2015。")
            return
        target = {"type": "national_standard", "code": STANDARD_CHOICES["gbt2015"]}
        if choice == "journal":
            try:
                target = {"type": "journal", "url": journal_guide_url(journal.get())}
            except ValueError:
                message.set("请输入有效的期刊官网或作者指南网址。")
                journal.focus_set()
                return
        output = selected_layout.get()
        if not output:
            message.set("请选择是否用于 LaTeX 排版。")
            return
        current_keys = {}
        if selected_ai.get() == "deepseek":
            api_key = key.get().strip() or configured_key
            model_id = model_entry.get().strip()
            if not api_key or not model_id:
                message.set("请填写 DeepSeek 的 API 密钥和模型。")
                (model_entry if api_key else key).focus_set()
                return
            current_keys["deepseek"] = (api_key, model_id)
        if captured_credentials is not None:
            captured_credentials.update(current_keys)
        result = {
            "status": "ok",
            "providers": list(current_keys),
            "bibliography_standard": target,
            "reference_export": "bibtex" if output == "latex" else "plain_text",
        }
        if current_keys:
            result["authorized_evidence_scope"] = DEEPSEEK_EVIDENCE_SCOPE
        window.destroy()

    buttons = ttk.Frame(frame)
    buttons.grid(row=11, column=0, columnspan=2, sticky="e", pady=("7p", 0))
    ttk.Button(buttons, text="取消", command=window.destroy, width=5).pack(side="left", padx=(0, "6p"))
    confirm = ttk.Button(buttons, text="确认设置", command=submit, style="Primary.TButton", width=9)
    confirm.pack(side="left")

    def update_api(*_):
        if selected_ai.get() == "deepseek":
            api_panel.grid()
            confirm.configure(text="确认并授权发送", width=16)
        else:
            api_panel.grid_remove()
            confirm.configure(text="确认设置", width=9)
        message.set("")

    selected_ai.trace_add("write", update_api)
    update_api()
    window.bind("<Return>", submit)
    if selected_standard.get() == "journal":
        journal.focus_set()
    elif not selected_standard.get():
        standard_buttons.winfo_children()[0].focus_set()
    elif not selected_layout.get():
        layout_buttons.winfo_children()[0].focus_set()
    else:
        confirm.focus_set()
    window.mainloop()
    return result or {"status": "cancelled"}


def review_session(providers, credentials):
    for line in sys.stdin:
        try:
            command = json.loads(line)
            action = command["action"]
            if action == "finish":
                return
            if action != "review":
                raise ValueError("Unknown session action.")
            bundle, items = load_bundle(Path(command["bundle"]))
            bundle_json, fingerprint = prepared_bundle(bundle)
            if command.get("approved_sha256") != fingerprint:
                raise ValueError("The evidence bundle no longer matches the checked local preview.")
            result = {"status": "ok", "bundle_sha256": fingerprint,
                      "providers": run_reviews(providers, bundle_json, items, credentials, 45)}
        except (KeyError, TypeError, OSError, ValueError):
            result = {"status": "error", "reason": "证据包或校验指纹无效，未发送。"}
        print(json.dumps(result, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai", choices=MODEL_CHOICES, default="codex")
    parser.add_argument("--standard", choices=STANDARD_CHOICES, default="")
    parser.add_argument("--journal-url", default="")
    parser.add_argument("--layout", choices=LAYOUT_CHOICES, default="")
    args = parser.parse_args()
    credentials = {}
    try:
        settings = choose_settings(args.ai, args.standard, args.journal_url, args.layout, credentials)
    except tk.TclError:
        parser.error("A desktop Python with Tk is required to open audit settings.")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(settings, ensure_ascii=False), flush=True)
    if (settings.get("providers") == ["deepseek"]
            and settings.get("authorized_evidence_scope") == DEEPSEEK_EVIDENCE_SCOPE):
        sys.stdin.reconfigure(encoding="utf-8")
        review_session(settings["providers"], credentials)


if __name__ == "__main__":
    main()
