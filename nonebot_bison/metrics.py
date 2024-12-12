from fastapi import APIRouter
from starlette.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

# Request counter
request_counter = Counter(
    "bison_request_counter", "The number of requests", ["site_name", "platform_name", "target", "success"]
)

# Sent counter
sent_counter = Counter("bison_sent_counter", "The number of sent messages", ["site_name", "platform_name", "target"])

metrics_router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@metrics_router.get("")
async def metrics():
    return Response(media_type=CONTENT_TYPE_LATEST, content=generate_latest())
