import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("PYTHON_ENV")
BASE_URL = os.getenv("BASE_URL", "")
TINKER_BASE_URL ="https://payments.tinker.co.ke"
is_prod_env = (ENV != "sdk_env") and (BASE_URL == "") 


class Config:
    API_KEY = os.getenv("TINKER_API_KEY")
    API_SECRET = os.getenv("TINKER_API_SECRET")
    BASE_URL = TINKER_BASE_URL if is_prod_env else BASE_URL