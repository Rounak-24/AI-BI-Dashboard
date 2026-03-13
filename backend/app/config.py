import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is required. Set it in .env\n"
        "Neon: postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require\n"
        "SQLite: sqlite:///./data/bi_dashboard.db"
    )
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

