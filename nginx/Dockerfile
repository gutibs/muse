FROM python:3.13-slim AS backend
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt
COPY backend/ .
RUN DJANGO_SECRET_KEY=build python manage.py collectstatic --noinput

FROM nginx:alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=backend /app/staticfiles /usr/share/nginx/static
