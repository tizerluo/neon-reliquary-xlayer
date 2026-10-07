"""Manual model play: one private identity and evidence log per scenario/seat.

This helper never chooses an action, loops, advances time or changes the game.
An agent observes, reasons, then supplies a command and its reason on stdin.
"""
import argparse
import datetime
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('scenario', choices=['m0', 'm1', 'm2', 'm3', 'edges'])
parser.add_argument('slot', type=int, choices=range(4))
parser.add_argument('action', choices=['join', 'observe', 'command', 'heartbeat', 'leave', 'events'])
parser.add_argument('--name', default='Codex QA')
args = parser.parse_args()
private = ROOT / '.qa-tmp' / 'mixed-play' / args.scenario
private.mkdir(parents=True, exist_ok=True)
identity_file = private / f'actor-{args.slot}.json'
observation_file = private / f'observation-{args.slot}.json'
evidence = ROOT / 'evidence' / 'mixed-play-ui' / args.scenario
evidence.mkdir(parents=True, exist_ok=True)
config = json.loads((ROOT / 'tools' / '.live-session.json').read_text())


def save_private(path, value):
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    path.write_text(json.dumps(value))


def call(name, values, observation=None):
    data = {'name': name, 'args': values}
    if observation is not None:
        data['observation'] = observation
    request = urllib.request.Request(config['url'] + '/call', json.dumps(data).encode(),
                                    headers={'Content-Type': 'application/json',
                                             'Authorization': 'Bearer ' + config['token']})
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)


def public(value):
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items() if k not in ('token', 'authorization')}
    if isinstance(value, list):
        return [public(v) for v in value]
    return value


started = time.time()
record = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'scenario': args.scenario, 'slot': args.slot, 'action': args.action}
if args.action == 'join':
    result = call('nr_join', {'slot': args.slot, 'name': args.name})
    if result.get('ok'):
        save_private(identity_file, {**result, 'seq': 0})
else:
    identity = json.loads(identity_file.read_text())
    auth = {k: identity[k] for k in ('agentId', 'token')}
    if args.action == 'observe':
        result = call('nr_observe', {'agentId': identity['agentId'], 'limit': 8})
        if result.get('ok'):
            save_private(observation_file, {'wallTime': time.time(), 'world': result})
        record['lease'] = call('nr_heartbeat', auth)
    elif args.action == 'command':
        import sys
        supplied = json.load(sys.stdin)
        reason = supplied.pop('reason', '')
        if not isinstance(reason, str) or not reason.strip():
            raise SystemExit('A model-written reason is required; no automatic policy is supplied.')
        observation = json.loads(observation_file.read_text())
        world = observation['world']
        identity['seq'] += 1
        save_private(identity_file, identity)
        order = {**supplied, **auth, 'seq': identity['seq'], 'runId': world['runId']}
        record.update(reason=reason, order=public(order),
                      observedGameTime=world.get('time'),
                      decisionWallSeconds=round(time.time() - observation['wallTime'], 3))
        result = call('nr_command', order,
                      {'runId': world['runId'], 'observedAt': world['observedAt']})
    elif args.action == 'events':
        result = call('nr_events', {'after': identity.get('eventCursor', 0), 'limit': 64})
        if result.get('ok'):
            identity['eventCursor'] = result['nextCursor']
            save_private(identity_file, identity)
    else:
        result = call('nr_' + args.action, auth)
record['requestWallSeconds'] = round(time.time() - started, 3)
record['result'] = public(result)
with (evidence / f'actor-{args.slot}.jsonl').open('a') as out:
    out.write(json.dumps(record, ensure_ascii=False) + '\n')
# Keep complete evidence on disk, but return only bounded decision-relevant fields.
if args.action == 'observe':
    view = {k: result.get(k) for k in ('ok', 'error', 'state', 'runId', 'time', 'leader',
                                      'expedition', 'command', 'enemyCount', 'slots', 'enemies')}
    view['units'] = [{k: v for k, v in unit.items() if k not in ('relics', 'chip')}
                     for unit in result.get('units', [])]
    print(json.dumps(view, ensure_ascii=False))
else:
    print(json.dumps(public(result), ensure_ascii=False))
