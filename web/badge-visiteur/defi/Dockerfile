FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==22.0.0
COPY app.py .
ENV FLAG="FPS{un_cookie_de_role_non_signe_cote_client}"
EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "2", "app:app"]
