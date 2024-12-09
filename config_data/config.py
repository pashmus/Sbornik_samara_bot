from dataclasses import dataclass
from environs import Env

amount_songs = 386
is_db_remote = False  # Переключение БД локальной или удалённой
path = ".env.remote" if is_db_remote else ".env"


@dataclass
class DbConfig:
    db_name: str
    db_host: str
    db_user: str
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
class AmountOfSongs:
    amount_songs: int


@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig
    card: BankCard
    amount_songs: AmountOfSongs


@dataclass
class ConfigLexicon:
    admin_username: str
    card: str
    amount_songs: int


def load_config() -> Config:
    env: Env = Env()
    env.read_env(path)
    return Config(tg_bot=TgBot(
        token=env("BOT_TOKEN"), admin_id=int(env("TG_ADMIN_ID")), admin_username=env("TG_ADMIN_USERNAME")),
        db=DbConfig(db_name=env("DATABASE"), db_host=env("DB_HOST"), db_user=env("DB_USER"),
                    db_password=env("DB_PASSWORD")), card=BankCard(card=env('DONATION_CARD')),
        amount_songs=AmountOfSongs(amount_songs=amount_songs))


def config_lexicon() -> ConfigLexicon:
    env: Env = Env()
    env.read_env(path)
    return ConfigLexicon(admin_username=env("TG_ADMIN_USERNAME"),
                         card=env("DONATION_CARD"),
                         amount_songs=amount_songs)