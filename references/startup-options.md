# 审查启动设置

调用 Skill 审查稿件、片段或参考文献表时，用本机带 Tk 和 Pillow 的桌面 Python 以可继续写入的终端会话（`tty: true`）启动 `python scripts/startup_options.py`。开始页沿用浅蓝单列弹窗，右上角显示 SKLMT 标识。已明确的设置可通过 `--standard journal|gbt2015`、`--journal-url`、`--layout latex|text` 和 `--ai codex|deepseek` 预填。窗口只返回公开设置。若用户看不到窗口，改用 `functions.request_user_input_async` 询问选项，并用单独掩码窗口录入密钥。等待选择时可并行提取本地稿件。

| 顺序 | 设置 | 选项 |
|---|---|---|
| 1 | 审查与著录规范 | 目标期刊，用户输入期刊官网或作者指南网址。可用 Ctrl+V 或单击「粘贴」。国标仅提供 GB/T 7714-2015。 |
| 2 | 是否用于 LaTeX 排版 | 是，生成独立 BibTeX（`.bib`）。否，按第 1 步所选规范生成独立纯文本（`.txt`）。 |
| 3 | 参与核验的模型 | 仅 Codex / DeepSeek + Codex。 |

## 核对规范并导出

- 选期刊时打开用户给的网页。若输入的是期刊首页，查找同一刊物最新的官方作者指南，并按适用文章类型核对规则。记录所用期刊和指南链接。
- 选国标时采用用户指定的 [GB/T 7714-2015](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=7FA63E9BBA56E60471AEDAEBDE44B14C)。可识别稿件采用的顺序编码或著者-出版年体例时沿用。仅有文末条目且体例无法判断时采用顺序编码并记入报告。由 Skill 按 [著录检查流程](audit-workflow.md#审查著录格式) 查阅选定版次的正文并应用条款。
- 根据 `reference_export` 生成一份 UTF-8 书目文件。`bibtex` 用核实后的书目字段生成 `.bib`。`plain_text` 按已选规范的编号、顺序和格式将文末条目写入 `.txt`。原编号可在逐条报告中追溯。问题索引、参考文献分布和逐条审查交付在同一份 PDF 中。

## 启用多 AI

选择 DeepSeek + Codex 时，同页显示 API 掩码密钥、模型和公开书目证据的发送范围。确认按钮为「确认并授权发送」。用户点击后，终端返回公开选项及 `authorized_evidence_scope: "bibliography_evidence"` 并保持会话，密钥只在当前进程中使用。保留终端会话 ID，按 [cross-ai.md](cross-ai.md) 核对证据包并运行，完成或取消后关闭会话。
