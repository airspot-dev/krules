
from djangae import environment

import threading

from django.conf import settings
import logging
logger = logging.getLogger(__name__)


def _redis_local_pubsub_run():
    import redis, rx, json, base64, uuid

    conn = redis.StrictRedis(**settings.LOCAL_PUBSUB_REDIS_CONNECT_KWARGS)
    pubsub = conn.pubsub()
    # try:
    pubsub.subscribe([settings.PUBSUB_TOPIC, ])
    logger.debug("Listening for %s" % settings.PUBSUB_TOPIC)
    for message in pubsub.listen():
        if message['type'] == 'message':
            envelope = json.loads(message['data'])
            data = json.loads((base64.b64decode(envelope['message']['data'])).decode('utf-8'))
            attributes = envelope['message'].get('attributes', None)
            subject = data['subject']
            payload = data['payload']
            logger.debug("received for subject: %s, payload: %s" % (subject, payload))
            if 'request_id' not in payload:
                payload['request_id'] = uuid.uuid4()

            results_subject = rx.subjects.ReplaySubject()
            extra = {
                'results_subject': results_subject
            }
            results = []
            results_subject.subscribe(results.append)

            action = settings.PUBSUB_TOPIC
            action_subjects = settings.ACTION_SUBJECTS
            # import pdb; pdb.set_trace()
            for action_subject in action_subjects:
                action_subject.on_next((action, subject, payload, extra))
            results_subject.dispose()
            logger.debug("results: %s" % str(results))


def subscribe_local():
    if environment.is_development_environment():
        t = threading.Thread(target=_redis_local_pubsub_run)
        t.setDaemon(True)
        t.start()
