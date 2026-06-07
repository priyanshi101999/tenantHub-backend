FROM python:3.11.9

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY . .

# Give permission to script
RUN chmod +x start.sh

# Run startup script
CMD ["./start.sh"]
