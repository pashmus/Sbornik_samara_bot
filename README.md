# Sbornik_samara_bot

## Настройка проекта
```shell
python -m venv venv
cp .env.example .env
```
В файле .env ввести свои данные



## Ресурсы по Webhook
https://docs.aiogram.dev/en/v3.1.1/api/methods/set_webhook.html



## Что-то настраивали с Витьком
ls -al ~/.ssh
ssh-keygen -t ed25519 -C "forjobav@gmail.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
git clone git@github.com:pashmus/Sbornik_samara_bot.git
cd Sbornik_samara_bot/
git pull
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
nano .env
cat .env


## Установка Python
sudo apt install python3.11-venv
python3 -m venv venv
source venv/bin/activate
python3 -V
deactivate
rm -rf venv
sudo apt-get uninstall python3
sudo apt-get remove python3
sudo apt install python3-venv
python3 -V
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


## PostgreSQL
sudo apt install postgresql postgresql-contrib
sudo apt-get remove postgresql
cd /
sudo apt install postgresql postgresql-contrib
pg_config --version
dpkg -s postgresql
service postgresql status
which postgres
find / -name "postgresql"
sudo systemctl status postgresql
createdb -U avp -h localhost -p 5432 -T tamplate0 sbornik_bot
sudo su postgres
exit
systemctl status postgresql
su - postgres
sudo -u postgres psql
exit
nano /etc/postgresql/16/main/postgresql.conf
nano /etc/postgresql/14/main/pg_hba.conf
systemctl restart postgresql   # Для рестарта БД достаточно одной команды