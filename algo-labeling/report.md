# Auto Labeling with Foundation Models — 实验报告

**任务**：用基础模型为公开数据集自动生成标签（五维数据笔试题 - 算法）
**代码**：`demo_code.py`　**输出**：`example_output.csv`、`summary.json`

---

## 1. Dataset and Task Description

| 项目 | 内容 |
|---|---|
| 数据集 | **IMDb 影评数据集**（HuggingFace `stanfordnlp/imdb`，5 万条影评，每条带人工情感标签） |
| 输入形态 | 英文长文本（电影评论，平均约 230 词，最长的达数千词） |
| 标注目标 | **情感二分类**：`positive` / `negative` |
| 实验规模 | 从 test split 抽取类别均衡的 **50 条**（25 正 / 25 负，seed=42 可复现） |

选择 IMDb 的原因：公开、规模适中、自带人工标签——可以直接计算「模型 vs 人」的一致率，满足笔试题第 3、4 节的要求。

## 2. Model and Method

### 2.1 Runnable Code（核心）

`demo_code.py` 支持两种后端：

- **`--backend hf`（默认）**：本地加载 `distilbert-base-uncased-finetuned-sst-2-english`（在 SST-2 情感语料上微调的 DistilBERT），**无需任何 API Key**，输入经截断至 512 token 后批量推理；
- **`--backend llm`（可选）**：调用任意 OpenAI 兼容接口（配置 `OPENAI_BASE_URL` / `OPENAI_API_KEY`），展示 LLM + Prompt 模板的标注方式，`temperature=0` 保证可复现。

运行方式：

```bash
pip install -r requirements.txt
python demo_code.py --num-samples 50 --backend hf
# 中国大陆网络建议：HF_ENDPOINT=https://hf-mirror.com python demo_code.py
```

输出两份文件：`example_output.csv`（每条影评：人工标签 / 模型标签 / 置信度 / 是否一致 / 原文）与 `summary.json`（总体准确率与分类别召回）。

### 2.2 Prompt Template（LLM 后端）

```
You are a sentiment labeling assistant.
Label the sentiment of the following movie review as exactly one word:
"positive" or "negative".

Examples:
Review: "An absolute masterpiece - the acting, the pacing, the score, everything works."
Label: positive
Review: "Two hours of my life I will never get back. Boring and predictable."
Label: negative

Now label this review:
Review: "{text}"
Label:
```

要求模型只输出一个单词，配合两个 few-shot 示例约束输出格式，便于程序解析。

**示例输出**（`example_output.csv` 第一行，节选）：

> human_label=`negative`　model_label=`negative`　model_score=`0.9993`　correct=`True`
> text=`"I rented this movie because of the casting of James Spader..."`

## 3. Result Analysis

DistilBERT-SST2 在 50 条 IMDb 测试样本上的总体准确率为 **84%**（正类召回 80%，负类召回 88%），对 50 条样本而言约等于人工水平的 85-90% 区间下沿。

**表现好的模式**：

- 情感词密集、观点鲜明的评论（"masterpiece"、"worst movie ever"），模型置信度普遍 >0.99；
- 正确样本的平均置信度 **0.972**，明显高于错误样本的 **0.916**，且全部 50 条中有 6 条置信度 <0.9——说明**置信度可以作为「需要人工复核」的有效信号**。

**失败模式**（8 条错例的共性）：

1. **褒贬混合的长评论**：如 "Beginning and end are pretty good, middle drags at times"——开头与结尾都是好话，但整体评价是负面的，模型被局部褒义词带偏；
2. **反讽 / 让步句式**："If you haven't enjoyed a Van Damme movie since bloodsport, you probably will not like this movie... **but I enjoy** these kinds of movies"——需要理解让步转折后的真实立场；
3. **用负面词汇写正面评价**：讨论争议题材的影评（"controversial", "hypocritical"）情感倾向实际为正，模型被词面极性误导；
4. **领域偏移 + 截断**：SST-2 训练语料是短句，IMDb 是数百词长文，512 token 截断可能丢掉位于文末的总结性观点。

## 4. Human vs Model Labeling

| 维度 | 人工标注 | 模型标注 |
|---|---|---|
| 速度 | 慢（1 条约 1-3 分钟） | 快（本 demo 50 条约 20 秒，可批量至每小时数万条） |
| 成本 | 高（按条计酬或占用人力） | 低（CPU 可跑，GPU 更快；LLM API 约 $0.0001-0.001/条） |
| 一致性 | 同一人前后可能不一致，多人之间需 IAA 校准 | 完全一致、可复现（temperature=0 时） |
| 语义理解 | 强：能处理反讽、语境、让步句式 | 弱项恰在反讽、混合情感、隐含立场 |
| 偏差 | 有主观偏差与疲劳效应 | 有训练数据偏差（SST-2 偏短评、偏英文） |

**结论**：二者互补——模型负责大规模粗标，人工负责高价值样本精标与边界样本复核。

## 5. Improvement Ideas（至少两条）

1. **置信度驱动的人机协同**：模型输出 `model_score`，低于阈值（如 0.9，本实验可覆盖全部 8 条错例中的大部分）的样本自动进入人工复核队列，用最低的人工成本把整体准确率推向接近人工水平（human-in-the-loop refinement）；
2. **多模型投票**：用 2-3 个不同架构/不同训练语料的模型（如 DistilBERT-SST2 + RoBERTa-imdb + 一个 LLM）分别标注，意见一致的样本直接采纳，分歧样本才送人工——比单模型更稳健；
3. **改进 Prompt / 任务描述**（LLM 路线）：在 Prompt 中明确「整体评价以最后结论为准」「注意让步与反讽」，并加入 2-3 条褒贬混合的 few-shot 示例；
4. **长文处理**：对超过 512 token 的评论做头尾拼接截断，或按段切分打分后聚合（mean/logit-sum），避免丢失文末观点。

---

### 附：复现说明

```bash
pip install -r requirements.txt
python demo_code.py --num-samples 50 --backend hf        # 复现本报告结果
python demo_code.py --num-samples 50 --backend llm       # LLM 标注（需配 API 环境变量）
```

summary.json：`{"accuracy": 0.84, "positive_recall": 0.80, "negative_recall": 0.88}`
