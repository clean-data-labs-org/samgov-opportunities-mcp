FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
# Needs APIFY_TOKEN at call time (not at startup): docker run -i --rm -e APIFY_TOKEN=... samgov-opportunities-mcp
ENTRYPOINT ["samgov-opportunities-mcp"]
