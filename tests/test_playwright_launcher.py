"""Verify the launcher passes Chrome settings through to MCP."""
import json
import os
import subprocess
from pathlib import Path

from conftest import REPO_DIR


def test_launcher_uses_chrome_and_cleans_up_config(tmp_path):
    npx = tmp_path / 'npx'
    npx.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
config = pathlib.Path(args[args.index('--config') + 1])
pathlib.Path(os.environ['CAPTURE']).write_text(json.dumps({
    'args': args, 'config': json.loads(config.read_text()), 'path': str(config)
}))
''')
    npx.chmod(0o755)
    capture = tmp_path / 'capture.json'
    env = {k: v for k, v in os.environ.items()
           if k.lower() not in ('http_proxy', 'https_proxy', 'all_proxy')}
    env.update(PATH=f'{tmp_path}:{env["PATH"]}', CAPTURE=str(capture),
               EXTRA_CHROMIUM_ARGS='--disable-dev-shm-usage')
    subprocess.run(['bash', str(REPO_DIR / 'scripts/playwright-mcp.sh')],
                   env=env, check=True)
    result = json.loads(capture.read_text())
    assert result['args'][-3:] == ['--browser', 'chrome', '--sandbox']
    launch = result['config']['browser']['launchOptions']
    assert launch['channel'] == 'chrome'
    assert launch['chromiumSandbox'] is True
    assert launch['headless'] is True
    assert launch['args'] == ['--disable-dev-shm-usage']
    assert 'executablePath' not in launch
    assert result['config']['browser']['isolated'] is True
    assert not Path(result['path']).exists()
