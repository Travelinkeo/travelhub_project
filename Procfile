web: gunicorn travelhub.wsgi:application
worker: celery -A travelhub worker --loglevel=info
beat: celery -A travelhub beat --loglevel=info
