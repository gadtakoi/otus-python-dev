##### 1. Login to heroku 
https://dashboard.heroku.com

##### 2. Create new app

https://dashboard.heroku.com/new-app

##### 3. Click Github tab

##### 4. Add repo 
https://github.com/gadtakoi/otus-python-dev

##### 5. Choose branch 
```
master
```

##### 6. Enable Automatic deploys 


##### 7. Tab Settings. Add variable to Config Vars
```
PROJECT_PATH=dz6
```

```dotenv
SECRET_KEY=<secret-key-secret-key-secret-key-secret-key-secret-key>
EMAIL_FROM_ADDRESS='example@gmail.com'
EMAIL_HOST='smtp.gmail.com'
EMAIL_HOST_USER='example@gmail.com'
EMAIL_HOST_PASSWORD='password'
EMAIL_PORT=587
EMAIL_USE_TLS=True
```

##### 8. Tab Settings. Add Buildpack`s
```git
https://github.com/timanovsky/subdir-heroku-buildpack.git
```
```
heroku/python
```

##### 9. Tab Resources. Add Heroku Postgres

##### 10. Optional. Manual deploy on tab Deploy 

##### 11. Optional. Logs view: 
```shell script
heroku labs:enable log-runtime-metrics -a dz6test
heroku restart
heroku logs --tail -a dz6test
```

##### 12. Fill with test data:
```shell script
heroku run bash -a dz6test
./manage.py generate_test_data
```


