"""Offline scoped gate recorder; no installs, native I/O, or root gate."""

import json
import subprocess
from pathlib import Path

ROOT = Path('/home/otto/dev/ro-bots')
OUT = ROOT / 'run/reviews/rest-interrupt-private'
OWN = ['src/robots/app/brain.py', 'src/robots/app/agent_runtime.py',
       'src/robots/app/playing_runtime.py', 'tests/test_native_rest_interrupt.py',
       'tests/test_rest_recovery_script.py']
TESTS = ['tests/test_native_rest_interrupt.py', 'tests/test_rest_recovery_script.py',
         'tests/test_native_pose_recovery.py', 'tests/test_native_playing_keepalive.py',
         'tests/test_brain.py', 'tests/test_agent_host.py', 'tests/test_empty_farm_plan.py',
         'tests/test_host_native_vitals.py', 'tests/test_host_native_transport.py',
         'tests/test_playing_startup_cleanup.py']
COMMANDS = {
    'black': ['.venv/bin/black', '--check', *OWN],
    'ruff': ['.venv/bin/ruff', 'check', *OWN],
    'mypy': ['.venv/bin/mypy', *OWN],
    'xenon': ['.venv/bin/xenon', 'src', '--max-absolute', 'B', '--max-modules', 'B', '--max-average', 'A'],
    'pylint': ['.venv/bin/pylint', '--disable=all', '--enable=duplicate-code', '--ignore-paths=tests', 'src'],
    'scoped-tests': ['.venv/bin/pytest', '-oaddopts=', '-pno:cacheprovider', *TESTS, '-q', '--junitxml='+str(OUT/'scoped-final.xml')],
    'playing-regressions': ['.venv/bin/pytest', '-oaddopts=', '-pno:cacheprovider', 'tests/test_playing_runtime.py', '-q', '--junitxml='+str(OUT/'playing-regressions.xml')],
}
results = {}
for name, command in COMMANDS.items():
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    log = OUT / (name+'-final.log')
    log.write_text(result.stdout+result.stderr)
    results[name] = {'command': command, 'returncode': result.returncode, 'log': str(log.relative_to(ROOT))}
    print(name, result.returncode, result.stdout[-2000:], result.stderr[-2000:], flush=True)
(OUT/'gate-results.json').write_text(json.dumps(results, indent=2)+'\n')
raise SystemExit(any(value['returncode'] for key,value in results.items() if key!='playing-regressions'))
