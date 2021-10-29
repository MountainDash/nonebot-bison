FROM python:3.9
RUN python3 -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
RUN python3 -m pip install poetry && poetry config virtualenvs.create false
WORKDIR /app
COPY ./pyproject.toml ./poetry.lock* /app/
RUN poetry install --no-root --no-dev
# RUN PYPPETEER_DOWNLOAD_HOST='http://npm.taobao.org/mirrors' pyppeteer-install
ADD src /app/src
ADD bot.py /app/
ENV HOST=0.0.0.0
CMD ["python", "bot.py"]
