"""Time one Shipyard replacement proposal. The host owns chat, checkpoints and dispatch."""

import json
import math
import sys
import time


WINDOW_SECONDS = 60


def timestamp(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('Expected a Unix timestamp in seconds')
    return value


def remaining(notified_at, now):
    return max(0, timestamp(notified_at) + WINDOW_SECONDS - timestamp(now))


def resolve(notified_at, replies, now):
    """Evaluate the delivered notice and the host's reconciled, time-stamped replies."""
    seconds_left = remaining(notified_at, now)
    status = 'pending'
    if not isinstance(replies, list):
        raise ValueError('Expected an ordered list of user replies')
    previous = notified_at
    for reply in replies:
        received = timestamp(reply['received_at'])
        if received < previous or received > now:
            raise ValueError('Replies must be ordered and fall between notice delivery and now')
        previous = received
        try:
            status = {'approve': 'approved', 'veto': 'vetoed', 'other': 'needs_clarification'}[reply['kind']]
        except KeyError as error:
            raise ValueError('Expected approve, veto or other') from error
        if status == 'vetoed':
            break
    if status == 'pending' and seconds_left == 0:
        status = 'timeout_default'
    return {'status': status, 'deadline': notified_at + WINDOW_SECONDS, 'seconds_left': seconds_left}


def main():
    request = json.load(sys.stdin)
    action = request['action']
    if action == 'wait':
        # A wake-up only. The coordinator still needs to reconcile queued replies.
        seconds = remaining(request['notified_at'], time.time())
        if seconds > WINDOW_SECONDS:
            raise ValueError('Notice delivery time is in the future')
        time.sleep(seconds)
        result = {'status': 'check_inbox'}
    elif action == 'resolve':
        now = time.time()
        if timestamp(request['notified_at']) > now:
            raise ValueError('Notice delivery time is in the future')
        result = resolve(request['notified_at'], request['replies'], now)
    else:
        raise ValueError('Expected wait or resolve')
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as error:
        sys.exit(f'Replacement window rejected: {error}')
