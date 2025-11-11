web: gunicorn travelhub.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A travelhub worker --loglevel=info --pool=solo
beat: celery -A travelhub beat --loglevel=info
