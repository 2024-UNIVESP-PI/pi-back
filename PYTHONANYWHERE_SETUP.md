# PythonAnywhere Deploy

This backend can run on PythonAnywhere's free plan using SQLite.

## 1. Create the PythonAnywhere app

1. Create or log into a PythonAnywhere account.
2. Open the **Consoles** tab.
3. Clone this repository into your PythonAnywhere home directory:

   ```bash
   git clone <your-pi-back-repo-url> ~/pi-back
   cd ~/pi-back
   ```

4. Create a virtualenv. Use PythonAnywhere's real Python 3.11 binary, not the `/usr/bin` symlink:

   ```bash
   mkvirtualenv --python=/usr/local/bin/python3.11 pi-back
   pip install -r requirements.txt
   ```

5. Prepare the database and static files:

   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   ```

## 2. Configure the Web tab

1. Go to **Web** > **Add a new web app**.
2. Choose **Manual configuration**.
3. Choose the Python version that matches your virtualenv.
4. Set **Source code** to:

   ```text
   /home/motokiyo/pi-back
   ```

5. Set **Working directory** to:

   ```text
   /home/motokiyo/pi-back
   ```

6. Set **Virtualenv** to:

   ```text
   /home/motokiyo/.virtualenvs/pi-back
   ```

## 3. Configure WSGI

Open the WSGI file from the PythonAnywhere **Web** tab and replace its contents with the contents of `pythonanywhere_wsgi.py.example`.

## 4. Configure environment variables

PythonAnywhere free accounts usually configure environment variables directly inside the WSGI file before `get_wsgi_application()`.

Add values like these before the final import:

```python
os.environ["SECRET_KEY"] = "replace-with-a-generated-secret-key"
os.environ["DEBUG"] = "False"
os.environ["ALLOWED_HOSTS"] = "motokiyo.pythonanywhere.com"
os.environ["CSRF_TRUSTED_ORIGINS"] = "https://arraia-tech.netlify.app,https://motokiyo.pythonanywhere.com"
os.environ["CORS_ALLOWED_ORIGINS"] = "https://arraia-tech.netlify.app"
os.environ["FRONTEND_URL"] = "https://arraia-tech.netlify.app"
os.environ["ADMIN_PASSWORD"] = "replace-with-a-private-admin-password"
```

Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 5. Configure static and media files

In the PythonAnywhere **Web** tab, add static file mappings:

```text
URL: /static/
Directory: /home/motokiyo/pi-back/staticfiles
```

```text
URL: /media/
Directory: /home/motokiyo/pi-back/media
```

## 6. Reload

Click **Reload** on the PythonAnywhere **Web** tab.

The backend should be available at:

```text
https://motokiyo.pythonanywhere.com/
```

The Django admin should be available at:

```text
https://motokiyo.pythonanywhere.com/admin/
```

## Updating Later

From a PythonAnywhere console:

```bash
cd ~/pi-back
git pull
workon pi-back
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Then reload the web app from the **Web** tab.
