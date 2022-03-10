FROM node:16 as frontend
ADD . /app
WORKDIR /app/admin-frontend
RUN yarn && yarn build

FROM python:3.9
RUN python3 -m pip install poetry && poetry config virtualenvs.create false
WORKDIR /app
COPY ./pyproject.toml ./poetry.lock* /app/
RUN poetry install --no-root --no-dev
ADD src /app/src
ADD bot.py /app/
COPY --from=frontend /app/src/plugins/nonebot_bison/admin_page/dist /app/src/plugins/nonebot_bison/admin_page/dist
ENV HOST=0.0.0.0
CMD ["python", "bot.py"]
