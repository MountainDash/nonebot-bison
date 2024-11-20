from prometheus_client import Counter

# Request counter
request_counter = Counter("bison_request_counter", "The number of requests")
# Success counter
success_counter = Counter("bison_success_counter", "The number of successful requests")

# Sent counter
sent_counter = Counter("bison_sent_counter", "The number of sent messages")
