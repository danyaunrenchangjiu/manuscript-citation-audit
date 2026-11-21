# PDF 数据结构

`scripts/render_report.py` 从一份 UTF-8 JSON 生成审查 PDF。顶层为 `manuscript`、`date`、`models` 和 `references`。索引、分布和逐条审查共用 `references`。

- `models` 含 Codex 初审，启用交叉核验时再加入 DeepSeek。每项包含 `status`（显示名称）及可选 `detail`（实际模型 ID 或调用状态）。按模型与核验结果的对应顺序排列。
- `references` 每项包含 `id`、`title`、可选的 `authors`、`sections` 和多模型时必填的 `summary`。`id` 用文末原编号或条目标识。
- 仅用 Codex 时，为每项填写 `issues`，列出文末条目的真实性疑点、书目差异、重复项或格式问题。无问题填 `[]`。缺少该字段时，首页计为「未标注问题状态」。
- 交叉核验时按 `models` 顺序填 `model_issues`，例如 `[[], ["文末 DOI 指向另一篇文献"]]`。保留任一模型独立发现的文末问题，含有争议的发现。无问题用 `[]`，该模型未返回可用结果时用 `null`。首页列出提出问题的模型。存在 `model_issues` 时，首页以该字段为依据。
- `sections` 含 `location`、`authenticity`、`support`、`format`。`location` 记录文末编号及位置，`authenticity` 给出身份结论、出版链接及书目字段差异，`support` 记录原文支持程度和证据出处。第 1–3 项的 `cells` 按 `models` 顺序提供，可含 `status` 和 `detail`。
- `format.shared` 只填一条核实后的可复制书目。必要字段待核时填待核提示。第 4 项通栏渲染。`links` 是含 `label`、`url` 的数组，可用于第 2–3 项的正式出版链接和原文证据链接。
- `source_type` 用于参考文献分布，取 `journal`、`non_journal` 或 `unverified`。`journal` 类型另填已核实的 `journal` 正式刊名。无法核实的书目条目填 `unverified`。每个文末条目标识提交一次。
- `summary` 提供通栏的第 5 项「交叉检验总结」，涵盖一致、分歧、未返回和采信证据。仅运行 Codex 时可省略，若提供则显示为不编号的「本条总评」。

模型输出中的真实性、书目信息和格式结果沿用原判定。对调用失败或未获授权的模型，标明实际状态。以正式出版记录与所选著录规范核实模型结论。
