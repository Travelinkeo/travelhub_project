web: gunicorn travelhub.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --threads 2
bot: python manage.py run_telegram_bot
worker: celery -A travelhub worker -l info -P gevent
beat: celery -A travelhub beat -l info
