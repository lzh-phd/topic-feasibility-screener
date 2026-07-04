# Topic Feasibility Screener

**First updated version / 第一次更新版**

`topic-feasibility-screener` is a Codex skill for screening empirical research topics from existing `.csv` or Stata `.dta` datasets. It combines dataset profiling, broad topic brainstorming, real literature search, transparent theory/data scoring, and second-pass validation into a visual HTML dashboard.

`topic-feasibility-screener` 是一个用于筛选实证研究选题的 Codex skill，支持从现有 `.csv` 或 Stata `.dta` 数据库出发，完成数据画像、开放式选题发散、真实文献检索、理论与数据可行性透明评分，以及前几个候选选题的二次验证，并最终生成可视化 HTML 报告。

This version is designed for early-stage thesis and paper development in accounting, finance, economics, management, corporate governance, digital transformation, ESG, audit, disclosure, and capital-market research.

本版本主要面向会计、金融、经济学、管理学、公司治理、数字化转型、ESG、审计、信息披露和资本市场等方向的论文或学位论文早期选题筛选。

## What Is New In The First Updated Version

## 第一次更新版的主要变化

- Visual HTML dashboard as the main output, not a spreadsheet-only workflow.
- 以可视化 HTML 报告作为主要输出，而不是只输出表格文件。
- Broader topic brainstorming from all usable variables and nearby datasets.
- 基于主数据与同目录附近数据集中的可用变量进行更开放的选题发散。
- Literature search diagnostics with query family, provider status, raw hits, valid hits, relevant hits, and error messages.
- 增加文献检索诊断，记录检索族、数据源状态、原始命中数、有效命中数、相关命中数和错误信息。
- Transparent 0-100 score display for overall feasibility, empirical feasibility, theory support, theory gap, topic alignment, paper relevance, source tier, and innovation-gap value.
- 对总体可行性、实证可行性、理论支持、理论缺口、选题匹配度、论文相关性、来源等级和创新缺口价值等指标采用 0-100 的百分制展示。
- Evidence classification into `direct`, `bridge`, `background`, and `weak`.
- 将文献证据分为 `direct`、`bridge`、`background` 和 `weak` 四类。
- Bridge literature is now treated as theoretically valuable when direct evidence is absent.
- 当直接证据缺失时，桥接文献会被视为具有理论价值，而不是被简单判定为无效。
- `evidence_profile` explains whether a topic has direct evidence, bridge support, one-sided background support, or weak theoretical footing.
- 新增 `evidence_profile`，用于说明选题是已有直接证据、存在桥接文献支持、只有单边背景文献，还是理论基础较弱。
- Top-three second-pass validation, including fixed-effect checks and placebo/permutation-style diagnostics where the data structure allows.
- 对排名前三的选题进行二次验证，在数据结构允许时包括固定效应检验和安慰剂/置换式诊断。
- Mandatory self-audit file (`feature_validation_checks.csv`) to verify data reading, brainstorming, literature diagnostics, evidence scoring, second-pass validation, and chart links.
- 强制生成自检文件 `feature_validation_checks.csv`，用于核验数据读取、选题发散、文献诊断、证据评分、二次验证和图表链接是否正常。

## Core Idea

## 核心思想

The skill does not treat a significant coefficient as a publishable result. It screens whether a research topic has both:

该 skill 不会把某个显著系数直接等同于可发表结论，而是筛查一个选题是否同时具备以下两类可行性：

1. **Theory feasibility**: a clear research question, adjacent literature, a plausible mechanism, and a credible research gap.
2. **Data feasibility**: usable variables, variation, sample size, interpretable roles, and a minimal empirical signal.

1. **理论可行性**：是否有清晰研究问题、相邻文献基础、合理机制和可信研究缺口。
2. **数据可行性**：是否有可用变量、足够变异、样本量、可解释的变量角色和初步实证信号。

The first updated version explicitly separates two situations that older keyword-only tools often confuse:

第一次更新版特别区分了传统关键词工具容易混淆的两种情况：

- **No theory footing**: little or no relevant literature appears.
- **Potential frontier gap**: no paper directly studies the exact relationship, but adjacent literatures provide bridge evidence.

- **缺乏理论基础**：几乎没有相关文献。
- **潜在前沿缺口**：尚无文献直接研究该关系，但相邻文献能够提供桥接支持。

This is important for exploratory research. A topic with `direct_evidence_hits = 0` can still be promising if bridge evidence is dense and conceptually close.

这对探索性研究很重要。即使一个选题的 `direct_evidence_hits = 0`，只要桥接文献足够密集且概念距离较近，它仍然可能是有价值的前沿选题。

## Main Script

## 主脚本

Use the visual research-topic lab:

使用可视化选题实验室：

```powershell
python scripts\research_topic_lab.py "path\to\data.dta" --topic "data resource recognition and corporate reputation"
```

With specified variables:

指定变量运行：

```powershell
python scripts\research_topic_lab.py "path\to\data.dta" `
  --topic "data resource recognition and corporate reputation" `
  --y ReputationScore `
  --x entry `
  --controls Size Lev ROA Growth BM Board Indep Top1 SOE Cashflow Loss `
  --id firm_id `
  --time year
```

With root-directory scanning for additional datasets:

扫描项目根目录下的其他数据集以拓展选题：

```powershell
python scripts\research_topic_lab.py "path\to\data.dta" `
  --topic "data resource recognition and corporate reputation" `
  --scan-root "path\to\project_folder" `
  --literature-top 30 `
  --per-query 8 `
  --deep-top 3 `
  --placebo-reps 200
```

## Outputs

## 输出文件

The main output is:

主要输出文件：

- `research_topic_lab_report.html`

Supporting audit files include:

辅助审计文件包括：

- `feature_validation_checks.csv`
- `topic_scores.csv`
- `second_pass_validation.csv`
- `literature_evidence.csv`
- `literature_query_diagnostics.csv`
- `external_data_profile.csv`
- `external_topic_ideas.csv`
- `variable_profile.csv`
- `summary.json`

Standalone chart pages are written under:

独立图表页面会输出到：

- `charts/`

## Scoring Overview

## 评分说明

All major dashboard scores are displayed on a 0-100 scale.

报告中的主要分数均采用 0-100 的百分制展示。

- **Empirical score**: first-pass regression signal plus second-pass validation for top topics.
- **实证可行性分数**：由初步回归信号和排名靠前选题的二次验证结果共同构成。
- **Theory support score**: paper-level evidence from source tier, relevance, recency, citations, method signals, mechanism signals, and evidence class.
- **理论支持分数**：综合文献来源等级、相关性、时效性、引用信号、方法信号、机制信号和证据类别。
- **Theory gap score**: rewards active but not saturated literatures and raises gap value when direct evidence is missing but bridge evidence is strong.
- **理论缺口分数**：奖励活跃但未过度饱和的文献领域；当直接证据缺失但桥接证据较强时，会提高创新缺口价值。
- **Topic alignment score**: keeps generated topics connected to the user's rough idea while still allowing broad brainstorming.
- **选题匹配度分数**：确保生成选题与用户给定的大致方向相关，同时保留开放式发散空间。
- **Innovation gap score**: separates a genuine theory vacuum from a frontier gap supported by adjacent literatures.
- **创新缺口分数**：区分真正缺乏理论基础的选题与由相邻文献支撑的前沿缺口。

Evidence classes:

证据类别：

- `direct`: both sides of the candidate relationship appear in the paper text.
- `direct`：候选关系的两侧概念都出现在文献文本中。
- `bridge`: adjacent concepts support the theoretical link, such as information assets, intellectual capital, intangible resources, data valuation, data disclosure, investor judgment, or information environment.
- `bridge`：相邻概念能够支持理论链条，例如信息资产、智力资本、无形资源、数据估值、数据披露、投资者判断或信息环境。
- `background`: useful one-sided or contextual evidence.
- `background`：有用的单边证据或背景性证据。
- `weak`: low relevance or insufficient anchors.
- `weak`：相关性较低或概念锚点不足。

## Guardrails

## 使用边界

- Do not treat screening significance as causal proof.
- 不要把筛选阶段的显著性视为因果证明。
- Do not call a topic publishable only because the dashboard ranks it highly.
- 不要仅因为报告排名较高就认定选题可以发表。
- Check `feature_validation_checks.csv` before trusting the report.
- 在信任报告之前，应先查看 `feature_validation_checks.csv`。
- Review `literature_evidence.csv` and `literature_query_diagnostics.csv` before relying on theory scores.
- 在依赖理论分数之前，应检查 `literature_evidence.csv` 和 `literature_query_diagnostics.csv`。
- Use manual academic judgment for final variable definitions, identification design, sample restrictions, and literature positioning.
- 最终变量定义、识别设计、样本约束和文献定位仍需人工学术判断。

## Installation

## 安装方式

Copy this folder into your Codex skills directory:

将该文件夹复制到你的 Codex skills 目录：

```powershell
C:\Users\<you>\.codex\skills\topic-feasibility-screener
```

Then invoke it in Codex:

然后在 Codex 中调用：

```text
[$topic-feasibility-screener] Here is my DTA/CSV. The rough topic is digital transformation and financing constraints. Please screen feasible topics and run minimal validation.
```

## License

## 许可证

MIT License.

MIT 许可证。
