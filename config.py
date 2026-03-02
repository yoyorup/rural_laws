"""Global configuration for the Rural Law Daily Review System."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "laws").mkdir(exist_ok=True)

# --- MySQL ---
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "rural_law_db")
MYSQL_UNIX_SOCKET = os.getenv("MYSQL_UNIX_SOCKET", "")  # e.g. /tmp/mysql.sock

# --- API ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-max")

GLM_API_KEY = os.getenv("GLM_API_KEY", "")
GLM_MODEL = os.getenv("GLM_MODEL", "glm-4")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "claude")

# --- Rural keywords for filtering ---
RURAL_KEYWORDS = [
    "农村", "农业", "农民", "土地", "乡村", "耕地",
    "承包", "宅基地", "集体", "合作社", "粮食",
    "种植", "养殖", "林地", "渔业", "牧业",
    "乡镇", "村委", "村集体", "振兴",
]

# --- Fetcher settings ---
REQUEST_TIMEOUT = 30          # seconds
REQUEST_RETRY_TIMES = 3
REQUEST_RETRY_BACKOFF = 2     # seconds
VERIFY_SSL = os.getenv("VERIFY_SSL", "false").lower() == "true"  # 是否验证 SSL

# NPC Law Database
NPC_BASE_URL = "https://flk.npc.gov.cn"
NPC_SEARCH_API = "https://flk.npc.gov.cn/api/"
NPC_SEARCH_KEYWORDS = ["农村", "农业", "土地", "乡村", "农民"]
NPC_DAYS_BACK = 30            # fetch laws published within last N days

# MOA (Ministry of Agriculture and Rural Affairs)
MOA_BASE_URL = "https://www.moa.gov.cn"
MOA_POLICY_URL = "https://www.moa.gov.cn/gk/zcfg/"

# News sources
NEWS_SOURCES = {
    "xinhua": "http://so.news.cn/",
    "farmer": "http://www.farmer.com.cn/",
    "people": "https://search.people.com.cn/s?keyword={keyword}",
}

# --- Claude processor ---
CLAUDE_SYSTEM_PROMPT = """你是一名专业的农村法律顾问。
给定一段法律条文，请按以下 JSON 格式输出：
{
  "clauses": [
    {
      "article_no": "第X条",
      "raw_text": "原文",
      "explanation": "通俗解读（2-3句话）",
      "example": "生活化举例（具体场景）"
    }
  ],
  "summary": "整部法律的一段话简介"
}
请确保输出是合法的 JSON，不要包含任何额外的文字或 markdown 代码块标记。"""

CLAUDE_MAX_TOKENS = 4096
CLAUDE_BATCH_SIZE = 10        # max articles per Claude call

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
