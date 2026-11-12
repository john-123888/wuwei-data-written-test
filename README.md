# 五维数据笔试题 / Wuwei Data Written Test

杭州五维数据有限责任公司笔试题的实现，包含五部分：

| 目录 | 题目 | 技术栈 |
|---|---|---|
| `frontend/` | 按设计稿实现页面 | HTML / CSS / 原生 JS |
| `backend/` | HelloWorld API + 登录 API | Spring Boot 3.2.0 + Spring Security |
| `crawler/` | 爬取 MIT Admissions 博客 | Playwright + DrissionPage（两版实现） |
| `fastapi-streaming/` | 流式 API demo | FastAPI |
| `algo-labeling/` | 基础模型自动标注数据集 | HuggingFace Transformers（IMDb 情感标注，84% 准确率） |

> 线上 Figma 设计稿：<https://www.figma.com/design/D0jjN7Twkq0DGm3ZJvQabz/>

---

## 1. 前端 `frontend/`

根据 Figma 设计稿实现的「Upload Your Resume」页面：

- 左侧：Finish! 标签、标题、说明文案、插画（SVG 重绘）
- 右侧：Upload File 卡片 —— 虚线拖放上传区、Last step / Finish 按钮
- 底部：4 步进度条（最后一步高亮）
- 支持拖拽 / 点击选择文件（最多 5 个）、响应式布局（≤900px 单列）

**运行**：直接用浏览器打开 `frontend/index.html` 即可，无需构建。

---

## 2. 后端 `backend/`

Spring Boot **3.2.0** + Spring Security 实现：

- `GET /api/hello` —— 需要 Spring Security 认证（HTTP Basic），返回字符串 `"Hello World"`
- `POST /api/login` —— 用户名密码登录接口，账号 `test` / 密码 `123456`，成功后返回可直接用于 Basic 认证的 `authorization` 字段
- 未认证访问 → `401 Unauthorized`

**运行**：

```bash
cd backend
mvn spring-boot:run        # 默认端口 8080
```

**验证**：

```bash
# 未认证 -> 401
curl -i http://localhost:8080/api/hello

# 认证后 -> "Hello World"
curl -u test:123456 http://localhost:8080/api/hello

# 登录接口
curl -X POST -H "Content-Type: application/json" \
     -d '{"username":"test","password":"123456"}' \
     http://localhost:8080/api/login
```

**测试**：`mvn test`，共 5 个用例（未认证 401 / 认证成功 / 密码错误 401 / 登录成功 / 登录失败），全部通过。

> 说明：演示用内存用户，密码以 `{noop}` 明文存储（`SecurityConfig` 中有注释），生产环境应改用 BCrypt。

---

## 3. 爬虫 `crawler/`

用 **Playwright** 和 **DrissionPage** 两种方式分别爬取 <https://mitadmissions.org/blogs/>，结果保存为 CSV。两版脚本字段一致：

| 列 | 说明 |
|---|---|
按题目要求，CSV 包含以下 6 列：

| 列 | 说明 |
|---|---|
| `Title` | 博客标题 |
| `Author` | 作者 |
| `Comment Count` | 评论数（Disqus 动态渲染，等待其加载后从列表页抓取，只保留数字） |
| `Time` | 发布日期 |
| `Article Content` | 文章正文（进入每篇内页抓取 `.article__body` 下的段落/列表，用换行拼接） |
| `Images In Article` | 正文内图片 URL，多张用 `;` 分隔 |

已抓取前 2 页共 **32 篇文章**（32/32 有正文与评论数，25/32 正文含图，其余文章本身无图）：

- `output/mit_blogs_playwright.csv`
- `output/mit_blogs_drissionpage.csv`

**实现思路**（两版一致）：

1. 先抓列表页 `/blogs/`、`/blogs/page/2/`，拿到每篇的标题、作者、日期、链接，并等待 4 秒让 Disqus 脚本渲染出评论数
2. 再逐篇访问文章内页，抓取正文段落与正文内图片

**运行**：

```bash
# Playwright 版
pip install -r requirements.txt
playwright install chromium
python playwright_crawler.py --pages 2

# DrissionPage 版（自动检测本机 Chrome/Edge）
python drissionpage_crawler.py --pages 2
```

两个脚本都支持 `--pages`（抓几页）与 `--output`（输出路径）参数，支持翻页（`/blogs/page/2/`）。

---

## 4. FastAPI 流式接口 `fastapi-streaming/`

`main.py` 实现三种流式响应：

| 端点 | 形式 |
|---|---|
| `GET /stream` | `StreamingResponse` 分块文本流 |
| `GET /stream-sse` | Server-Sent Events（`text/event-stream`） |
| `GET /stream-lines?count=5` | NDJSON 逐行 JSON 流（模拟 LLM token 输出） |

**运行**：

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

交互式文档：<http://localhost:8000/docs>

---

## 5. 基础模型自动标注 `algo-labeling/`

用基础模型给公开数据集自动打标签（笔试题-算法）：

- **数据集**：IMDb 影评（`stanfordnlp/imdb`），对 50 条类别均衡的测试样本做情感标注
- **模型**：默认 `distilbert-base-uncased-finetuned-sst-2-english`，**本地运行、无需 API Key**；另提供 OpenAI 兼容接口的 LLM 后端（含 Prompt 模板）
- **结果**：总体准确率 84%（正类召回 80% / 负类 88%），报告中含误差分析、人机对比与改进方案
- **文件**：`demo_code.py`（可运行代码）、`example_output.csv`（示例输出）、`summary.json`（指标）、`report.md`（1-2 页报告）

**运行**：

```bash
cd algo-labeling
pip install -r requirements.txt
python demo_code.py --num-samples 50 --backend hf
# 中国大陆网络建议加镜像：HF_ENDPOINT=https://hf-mirror.com python demo_code.py
```

详见 [`algo-labeling/report.md`](algo-labeling/report.md)。

---

## 环境要求

- 后端：JDK 17+、Maven 3.8+
- 爬虫：Python 3.10+，Playwright 版需 `playwright install chromium`；DrissionPage 版需本机有 Chrome 或 Edge
- FastAPI：Python 3.9+
- 自动标注：Python 3.10+，首次运行会自动从 HF 镜像下载模型（约 268MB）与数据集
