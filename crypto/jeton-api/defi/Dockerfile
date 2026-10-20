FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==22.0.0
COPY app.py .
ENV FLAG="FPS{aes_ctr_nonce_fixe_bitflip_vers_admin}"
EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "2", "--preload", "app:app"]
