web: python manage.py runserver
bot: python manage.py run_telegram_bot
worker: celery -A travelhub worker -l info -P gevent
beat: celery -A travelhub beat -l info
