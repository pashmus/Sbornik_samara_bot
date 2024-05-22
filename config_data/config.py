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


def load_config(path: str | None = None) -> Config:
    env: Env = Env()
    env.read_env()

    return Config(tg_bot=TgBot(
        token=env('BOT_TOKEN'), admin_id=env('tg_admin_id'), admin_username=env('tg_admin_username')),
        db=DbConfig(database=env('DATABASE'), db_host=env('HOST'), db_user=env('USER'), db_password=env('PASSWORD')),
        card=BankCard(card=env('my_card_num')))
