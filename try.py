import dotenv
import os

dotenv.load_dotenv()
print(type(int(os.getenv('TG_ADMIN_ID'))))