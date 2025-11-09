import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("TINKER_API_KEY")
    BASE_URL = os.getenv("TINKER_BASE_URL")
    API_SECRET = os.getenv("TINKER_API_SECRET")