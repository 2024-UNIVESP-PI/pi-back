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

4. Create a virtualenv using Python 3.12, which matches the repository and Django 4.2's supported versions:

   ```bash
   mkvirtualenv --python=/usr/local/bin/python3.12 pi-back
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
os.environ["ADMIN_USERNAME"] = "admin"
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

## GitHub Actions deployment

The backend workflow updates this checkout over SSH, runs migrations and
`collectstatic`, then reloads the web app through the PythonAnywhere API.
PythonAnywhere documents SSH access for paid accounts; on a free account this
workflow cannot run the remote maintenance commands.

1. Generate a dedicated deployment key locally:

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/pi-back-github-actions -C "pi-back-github-actions"
   ```

2. Add the public key (`.pub`) to `~/.ssh/authorized_keys` on PythonAnywhere.
3. Add the private key contents as the GitHub Actions secret
   `PYTHONANYWHERE_SSH_PRIVATE_KEY` in the `pi-back` repository.
4. Keep the existing `PYTHONANYWHERE_API_TOKEN`, `PYTHONANYWHERE_HOST`,
   `PYTHONANYWHERE_USERNAME` and `PYTHONANYWHERE_DOMAIN` secrets.

The remote checkout must already exist at `/home/<username>/pi-back`, with the
`pi-back` virtualenv configured as shown above. The workflow deploys only from
`main` or from a manual `workflow_dispatch` run.
