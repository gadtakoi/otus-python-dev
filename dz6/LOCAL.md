## Local setup

### Python
```shell script
sudo apt install python3.8
sudo apt install python3.8-dev
```

### Setup DB
```shell script
sudo -u postgres psql -c 'create database dz6_qna;'
sudo -u postgres psql
CREATE ROLE dz6_qna WITH LOGIN PASSWORD 'dz6_qna';
GRANT ALL PRIVILEGES ON DATABASE dz6_qna TO dz6_qna;
ALTER USER dz6_qna CREATEDB;
```
### Virtualenv

```shell script
cd dz6
virtualenv -p /usr/bin/python3.8 venv
source venv/bin/activate
```


### Setup project
```shell script
pip install -r requirements.txt
```

```shell script
python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser
```

### Generate test users, tags, question and answers
```shell script
python manage.py generate_test_data
```

### Run dev server
```shell script
python manage.py runserver
```
