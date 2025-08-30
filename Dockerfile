FROM python:3.9-slim


\u0646\u0635\u0628 \u0648\u0627\u0628\u0633\u062a\u06af\u06cc\u200c\u0647\u0627\u06cc \u0633\u06cc\u0633\u062a\u0645\u06cc \u0645\u0648\u0631\u062f \u0646\u06cc\u0627\u0632

RUN apt-get update && apt-get install -y \
    zlib1g-dev \
    libjpeg-dev \
    libfreetype6-dev \
    fonts-dejavu \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app


\u06a9\u067e\u06cc \u0641\u0627\u06cc\u0644\u200c\u0647\u0627\u06cc \u0645\u0648\u0631\u062f \u0646\u06cc\u0627\u0632

COPY requirements.txt .
COPY bot_reliable.py .
COPY .env .


\u0646\u0635\u0628 \u0648\u0627\u0628\u0633\u062a\u06af\u06cc\u200c\u0647\u0627\u06cc \u067e\u0627\u06cc\u062a\u0648\u0646

RUN pip install --no-cache-dir -r requirements.txt


\u067e\u0648\u0631\u062a \u0645\u0648\u0631\u062f \u0646\u06cc\u0627\u0632

EXPOSE 8000


\u062f\u0633\u062a\u0648\u0631 \u0627\u062c\u0631\u0627

CMD ["python", "bot_reliable.py"]
