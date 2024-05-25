from dataclasses import dataclass
from environs import Env

@dataclass
class DbConfig:
    database: str
    db_host: str
    db_user: str
    db_password: str

@dataclass
class TgBot:
    token: str
    admin_id: int
    admin_username: int

@dataclass
class BankCard:
    card: str


@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig
    card: BankCard


def load_config(path: str | None = None):
    env: Env = Env()
    env.read_env(path)

    # token=env("BOT_TOKEN")
    # admin_id=env("TG_ADMIN_ID")
    # admin_username=env("TG_ADMIN_USERNAME")
    # database=env("DATABASE")
    # db_host=env("HOST")
    # db_user=env("USER")
    # db_password=env("PASSWORD")
    # card=env('DONATION_CARD')

    return {
        'token':env("BOT_TOKEN"),
        'admin_id':env("TG_ADMIN_ID"),
        'admin_username':env("TG_ADMIN_USERNAME"),
        'database':env("DATABASE"),
        'db_host':env("HOST"),
        'db_user':env("USER"),
        'db_password':env("PASSWORD"),
        'card':env('DONATION_CARD')
    }

# def load_config(path: str | None = None) -> Config:
#     env: Env = Env()
#     env.read_env(path)
#
#     return Config(tg_bot=TgBot(
#         token=env("BOT_TOKEN"), admin_id=env("TG_ADMIN_ID"), admin_username=env("TG_ADMIN_USERNAME")),
#         db=DbConfig(database=env("DATABASE"), db_host=env("HOST"), db_user=env("USER"), db_password=env("PASSWORD")),
#         card=BankCard(card=env('DONATION_CARD')))
