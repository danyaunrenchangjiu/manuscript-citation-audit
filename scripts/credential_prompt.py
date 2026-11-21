"""Collect provider credentials in a local, masked dialog."""


def prompt_credentials(providers, existing, defaults, fingerprint):
    import tkinter as tk
    from tkinter import ttk

    from audit_ui import bind_paste, blue_dialog

    window, frame = blue_dialog("多 AI 交叉核验", "输入本次核验的 API 密钥")
    ttk.Label(frame, text=f"证据包指纹 {fingerprint[:12]}", style="Hint.TLabel").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(4, 9))

    names = {"openai": "OpenAI", "deepseek": "DeepSeek"}
    fields = {}
    for index, provider in enumerate(providers):
        name = names[provider]
        row = 2 + 2 * index
        ttk.Label(frame, text=f"{name} API 密钥").grid(row=row, column=0, sticky="w", padx=(0, 12))
        key = ttk.Entry(frame, width=38, show="*")
        key.grid(row=row, column=1, sticky="ew", pady=3)
        key.bind("<<Copy>>", lambda event: "break")
        key.bind("<<Cut>>", lambda event: "break")
        bind_paste(key)
        ttk.Label(frame, text=f"{name} 模型").grid(row=row + 1, column=0, sticky="w", padx=(0, 12))
        model = ttk.Entry(frame, width=38)
        model.insert(0, existing[provider][1] or defaults[provider])
        model.grid(row=row + 1, column=1, sticky="ew", pady=3)
        fields[provider] = (key, model)

    row = 2 + len(fields) * 2
    message = tk.StringVar(value="已配置的本机密钥可留空使用。")
    ttk.Label(frame, textvariable=message).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 10))
    result = None

    def submit(event=None):
        nonlocal result
        entered = {}
        for provider, (key, model) in fields.items():
            api_key = key.get().strip() or existing[provider][0]
            model_id = model.get().strip()
            if not api_key or not model_id:
                message.set(f"请填写 {names[provider]} 的密钥和模型。")
                (model if api_key else key).focus_set()
                return
            entered[provider] = (api_key, model_id)
        result = entered
        window.destroy()

    buttons = ttk.Frame(frame)
    buttons.grid(row=row + 1, column=0, columnspan=2, sticky="e")
    ttk.Button(buttons, text="取消", command=window.destroy).pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="运行核验", command=submit, style="Primary.TButton").pack(side="left")
    window.bind("<Return>", submit)
    next(iter(fields.values()))[0].focus_set()
    window.mainloop()
    return result
