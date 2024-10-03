FROM node:20.17.0 as frontend
ADD . /app
WORKDIR /app/admin-frontend
RUN npm install -g pnpm
RUN pnpm install && pnpm build

FROM python:3.11
RUN python3 -m pip install poetry && poetry config virtualenvs.create false
WORKDIR /app
COPY ./README.md ./pyproject.toml ./poetry.lock* /app/
RUN poetry install --only=main,docker
ADD src /app/src
ADD bot.py /app/
COPY --from=frontend /app/nonebot_bison/admin_page/dist /app/nonebot_bison/admin_page/dist
ENV HOST=0.0.0.0
CMD ["nb", "run"]
