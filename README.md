# Address Book

Simple address book application. Users have their contacts and contact groups. A user can create contacts, contact groups, and assign contacts to groups.

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

License: MIT

## Running Locally
    
1. Install [PostgreSQL](https://www.postgresql.org/download/)
2. Set up virtual environment:
```bash
    $ python -m venv venv
    $ source venv/bin/activate
    $ pip install -r requirements/local.txt
```
3. (Optional) Set up a password for `postgres` user, if you don't already have one
```bash
    $ sudo -u postgres psql
    postgres=# \password postgres
    Enter new password for user "postgres": <your-password>
    postgres=# \q
```
4. Run the following:
```bash
    $ sudo -u postgres createdb address_book
    $ export DATABASE_URL=postgres://postgres:<your-password>@127.0.0.1:5432/address_book
    $ python manage.py migrate
    $ python manage.py runserver 0.0.0.0:8000
```

### On Docker (Recommended)
1. Install and launch [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Run: `docker compose --file local.yml up`

### Final steps
Visit http://127.0.0.1:8000/ to create a user (API prevents unauthorized access) - go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

SwaggerUI for the API is available at http://127.0.0.1:8000/api/docs/

## Settings

Moved to [settings](http://cookiecutter-django.readthedocs.io/en/latest/settings.html).

### Type checks

Running type checks with mypy:

    $ mypy address_book

#### On Docker

    $ docker compose --file local.yml run --rm django mypy address_book

### Linters

Running style checks with flake:

    $ flake8 address_book

#### On Docker

    $ docker compose --file local.yml run --rm django flake8 address_book

### Formatters

Sorting imports with isort:

    $ isort address_book

#### On Docker

    $ docker compose --file local.yml run --rm django isort address_book


### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    $ coverage run -m pytest
    $ coverage report
    $ coverage html
    $ open htmlcov/index.html

#### Running tests with pytest

    $ pytest

#### On Docker

    $ docker compose --file local.yml run --rm django bash -c "coverage run -m pytest && coverage report"
    $ docker compose --file local.yml run --rm django coverage html
    $ docker compose --file local.yml run --rm django pytest
