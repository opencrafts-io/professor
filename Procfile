web: sh -c "pip install -r requirements.txt && python manage.py migrate && gunicorn --workers 1 --bind 0.0.0.0:8000 professor.wsgi:application --access-logfile - --error-logfile -"
