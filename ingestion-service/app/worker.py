import asyncio
import logging
from base64 import b64encode

from google.cloud import pubsub_v1

from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas.ingest import PubSubPushEnvelope, PubSubPushMessage
from app.services.ingestion_service import IngestionService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingestion-worker")


def _subscription_path(subscriber: pubsub_v1.SubscriberClient) -> str:
    if not settings.PUBSUB_SUBSCRIPTION:
        raise RuntimeError("PUBSUB_SUBSCRIPTION must be set for the ingestion worker")
    if "/" in settings.PUBSUB_SUBSCRIPTION:
        return settings.PUBSUB_SUBSCRIPTION
    return subscriber.subscription_path(settings.GCP_PROJECT_ID, settings.PUBSUB_SUBSCRIPTION)


async def _ingest_message(envelope: PubSubPushEnvelope) -> None:
    db = SessionLocal()
    try:
        service = IngestionService(db=db)
        await service.trigger_pubsub_ingestion(envelope)
    finally:
        db.close()


def _callback(message: pubsub_v1.subscriber.message.Message) -> None:
    envelope = PubSubPushEnvelope(
        message=PubSubPushMessage(
            data=b64encode(message.data).decode("utf-8"),
            messageId=message.message_id,
            publishTime=message.publish_time.isoformat() if message.publish_time else None,
            attributes=dict(message.attributes or {}),
        )
    )
    try:
        logger.info("Processing Pub/Sub message %s", message.message_id)
        asyncio.run(_ingest_message(envelope))
    except Exception:
        logger.exception("Failed to ingest Pub/Sub message %s", message.message_id)
        message.nack()
        return
    message.ack()
    logger.info("Acked Pub/Sub message %s", message.message_id)


def main() -> None:
    flow_control = pubsub_v1.types.FlowControl(max_messages=settings.PUBSUB_WORKER_MAX_MESSAGES)
    with pubsub_v1.SubscriberClient() as subscriber:
        subscription_path = _subscription_path(subscriber)
        logger.info("Starting ingestion worker for %s", subscription_path)
        future = subscriber.subscribe(subscription_path, callback=_callback, flow_control=flow_control)
        try:
            future.result()
        except KeyboardInterrupt:
            logger.info("Stopping ingestion worker")
            future.cancel()
            future.result()


if __name__ == "__main__":
    main()
