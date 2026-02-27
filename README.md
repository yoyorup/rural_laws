# 农村法律每日速览系统V1

自动抓取全国人大、农业农村部等权威来源的涉农法律法规，经 AI 逐条解读后生成静态 HTML 报告，方便农村工作者、基层法律服务人员及农业从业者快速掌握最新政策动态。

## 功能特性

- **多源抓取**：同时采集全国人大法律数据库（NPC）和农业农村部（MOA）发布的法规政策
- **智能过滤**：按农村关键词（农村、土地、宅基地、承包、合作社等）筛选相关法律条文
- **AI 解读**：调用大模型逐条生成通俗解读和生活化举例，降低法律阅读门槛
- **关联新闻**：自动抓取每部法律的相关新闻报道，提供政策背景
- **静态报告**：生成可直接用浏览器打开的 HTML 报告（首页 + 法律详情页 + 历史存档）
- **定时调度**：内置每日 00:00（Asia/Shanghai）自动运行的定时任务
- **多 AI 提供商**：支持 Claude、OpenAI、通义千问（Qwen）、智谱 GLM、Gemini，可灵活切换

## 项目结构

```
rural_law/
├── main.py              # CLI 入口
├── pipeline.py          # 核心流水线编排
├── config.py            # 全局配置（读取 .env）
├── requirements.txt
├── fetchers/
│   ├── npc_fetcher.py   # 全国人大法律数据库抓取
│   ├── moa_fetcher.py   # 农业农村部政策抓取
│   └── news_fetcher.py  # 关联新闻抓取
├── processors/
│   ├── law_filter.py    # 农村相关性过滤
│   ├── deduplicator.py  # 批次内去重 & 数据库去重
│   ├── law_processor.py # AI 处理调度
│   └── ai_providers/    # AI 提供商适配层
│       ├── base.py
│       ├── claude_provider.py
│       ├── openai_provider.py
│       ├── qwen_provider.py
│       ├── glm_provider.py
│       ├── gemini_provider.py
│       └── factory.py
├── generators/
│   └── html_generator.py  # Jinja2 HTML 生成
├── database/
│   ├── db_manager.py    # SQLite 读写操作
│   ├── models.py        # 数据模型（dataclass）
│   └── schema.sql       # 建表 SQL
├── scheduler/
│   └── cron_job.py      # APScheduler 定时任务
├── templates/           # Jinja2 HTML 模板
│   ├── base.html
│   ├── index.html
│   ├── law_detail.html
│   └── archive.html
├── data/                # SQLite 数据库（运行后自动生成）
└── output/              # 生成的 HTML 文件（运行后自动生成）
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制并编辑 `.env` 文件：

```bash
cp .env.example .env
```

`.env` 示例：

```env
# 选择默认 AI 提供商：claude | openai | qwen | glm | gemini
DEFAULT_AI_PROVIDER=claude

# 按需填写对应提供商的 API Key
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
QWEN_API_KEY=...
GLM_API_KEY=...
GEMINI_API_KEY=...

# 可选：自定义模型
CLAUDE_MODEL=claude-opus-4-6
OPENAI_MODEL=gpt-4o
QWEN_MODEL=qwen-max
GLM_MODEL=glm-4
GEMINI_MODEL=gemini-2.0-flash

# 可选：日志级别（DEBUG / INFO / WARNING / ERROR）
LOG_LEVEL=INFO
```

### 3. 初始化数据库

```bash
python main.py --init-db
```

### 4. 立即运行

```bash
# 抓取今天的数据并生成报告
python main.py --run-now

# 抓取指定日期的数据
python main.py --run-now --date 2026-02-27

# 指定 AI 提供商（覆盖 .env 配置）
python main.py --run-now --ai-provider openai
```

运行完成后，用浏览器打开 `output/index.html` 即可查看报告。

### 5. 仅重新生成 HTML

在不重新抓取数据的情况下，从数据库重新渲染页面：

```bash
python main.py --generate-only --date 2026-02-27
```

### 6. 启动定时调度

每日 00:00（北京时间）自动执行完整流水线：

```bash
python main.py --schedule
```

按 `Ctrl+C` 停止。

## 流水线说明

```
抓取 (NPC + MOA)
    ↓
批次内去重
    ↓
农村相关性过滤（关键词匹配）
    ↓
数据库去重（新增 / 更新 / 无变化）
    ↓
持久化到 SQLite
    ↓
AI 逐条解读（可选，需配置 API Key）
    ↓
抓取关联新闻
    ↓
生成静态 HTML 报告
```

## 支持的 AI 提供商

| 提供商 | 参数名 | 默认模型 | 环境变量 |
|--------|--------|----------|----------|
| Anthropic Claude | `claude` | `claude-opus-4-6` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai` | `gpt-4o` | `OPENAI_API_KEY` |
| 阿里通义千问 | `qwen` | `qwen-max` | `QWEN_API_KEY` |
| 智谱 GLM | `glm` | `glm-4` | `GLM_API_KEY` |
| Google Gemini | `gemini` | `gemini-2.0-flash` | `GEMINI_API_KEY` |

未配置 API Key 时，AI 解读步骤将自动跳过，其余步骤正常执行。

## CLI 参数一览

```
python main.py [选项]

选项：
  --run-now               立即执行完整流水线
  --date YYYY-MM-DD       指定目标日期（默认：今天）
  --generate-only         仅重新生成 HTML，不抓取数据
  --schedule              启动每日定时调度
  --init-db               初始化数据库
  --ai-provider PROVIDER  指定 AI 提供商（claude/openai/qwen/glm/gemini）
  --log-level LEVEL       日志级别（DEBUG/INFO/WARNING/ERROR）
```

## 数据来源

- **全国人大法律数据库**：https://flk.npc.gov.cn
- **农业农村部政策法规**：https://www.moa.gov.cn/gk/zcfg/

## 许可证

MIT
