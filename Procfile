# Procfile para Railway/Render/Heroku
web: gunicorn travelhub.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A travelhub worker --loglevel=info
beat: celery -A travelhub beat --loglevel=info
