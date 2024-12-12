from fastapi import APIRouter
from starlette.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

# Request counter
request_counter = Counter("bison_request_counter", "The number of requests")
# Success counter
success_counter = Counter("bison_success_counter", "The number of successful requests")

# Sent counter
sent_counter = Counter("bison_sent_counter", "The number of sent messages")
metrics_router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@metrics_router.get("")
async def metrics():
    return Response(media_type=CONTENT_TYPE_LATEST, content=generate_latest())
