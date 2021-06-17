FROM python:3.9
RUN echo "deb http://mirrors.aliyun.com/debian/ buster main contrib non-free\ndeb http://mirrors.aliyun.com/debian/ buster-updates main contrib non-free" > /etc/apt/sources.list
RUN   apt-get update && apt-get install -y fonts-wqy-microhei chromium
RUN python3 -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
RUN python3 -m pip install poetry && poetry config virtualenvs.create false
WORKDIR /app
COPY ./pyproject.toml ./poetry.lock* /app/
RUN poetry install --no-root --no-dev
# RUN PYPPETEER_DOWNLOAD_HOST='http://npm.taobao.org/mirrors' pyppeteer-install
COPY . /app/
ENV HOST=0.0.0.0
CMD ["python", "bot.py"]
