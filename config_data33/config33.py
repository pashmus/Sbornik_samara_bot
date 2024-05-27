from dataclasses import dataclass
from environs import Env


@dataclass
class dbConfig11:
    database: str
    db_host: str
    db_user11: str
    db_password: str


@dataclass
class TgBot:
    token: str
    admin_id: int
    admin_username: str


@dataclass
class BankCard:
    card: str


@dataclass
class Config22:
    tg_bot: TgBot
    db: dbConfig11
    card: BankCard


def load_config(path: str | None = None) -> Config22:
    env: Env = Env()
    env.read_env(path)

    return Config22(tg_bot=TgBot(
        token=env("BOT_TOKEN"), admin_id=env("TG_ADMIN_ID"), admin_username=env("TG_ADMIN_USERNAME")),
        db=dbConfig11(database=env("DATABASE"), db_host=env("HOST"), db_user11=env("USER"), db_password=env("PASSWORD")),
        card=BankCard(card=env('DONATION_CARD')))

#
# def load_config(path: str | None = None):
#     env: Env = Env()
#     env.read_env(path)
#
#     # token=env("BOT_TOKEN")
#     # admin_id=env("TG_ADMIN_ID")
#     # admin_username=env("TG_ADMIN_USERNAME")
#     # database=env("DATABASE")
#     # db_host=env("HOST")
#     # db_user=env("USER")
#     # db_password=env("PASSWORD")
#     # card=env('DONATION_CARD')
#
#     return {
#         'token':env("BOT_TOKEN"),
#         'admin_id':env("TG_ADMIN_ID"),
#         'admin_username':env("TG_ADMIN_USERNAME"),
#         'database':env("DATABASE"),
#         'db_host':env("HOST"),
#         'db_user':env("USER"),
#         'db_password':env("PASSWORD"),
#         'card':env('DONATION_CARD')
#     }


# def load_config(path: str | None = None) -> Config:
#     dotenv.load_dotenv(path)
#
#     return Config(tg_bot=TgBot(
#         token=os.getenv("BOT_TOKEN"), admin_id=int(os.getenv("TG_ADMIN_ID")),
#         admin_username=os.getenv("TG_ADMIN_USERNAME")),
#         db=DbConfig(database=os.getenv("DATABASE"), db_host=os.getenv("HOST"), db_user=os.getenv("USER"),
#                     db_password=os.getenv("PASSWORD")),
#         card=BankCard(card=os.getenv('DONATION_CARD')))

#
# def load_config(path: str | None = None):
#     env: Env = Env()
#     env.read_env(path)
#
#     # token=env("BOT_TOKEN")
#     # admin_id=env("TG_ADMIN_ID")
#     # admin_username=env("TG_ADMIN_USERNAME")
#     # database=env("DATABASE")
#     # db_host=env("HOST")
#     # db_user=env("USER")
#     # db_password=env("PASSWORD")
#     # card=env('DONATION_CARD')
#
#     return {
#         #'token':env("BOT_TOKEN"),
#         'admin_id':env("TG_ADMIN_ID"),
#         'admin_username':env("TG_ADMIN_USERNAME"),
#         'database':env("DATABASE"),
#         'db_host':env("HOST"),
#         #'db_user':env("USER"),
#         #'db_password':env("PASSWORD"),
#         'card':env('DONATION_CARD')
#     }