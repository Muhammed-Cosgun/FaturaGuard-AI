"""Native kütüphane kapanışı Python istisnasıyla yakalanamadığı için subprocess kullanır."""

import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent


def test_testclient_releases_native_validator_before_its_thread_stops() -> None:
    program = dedent("""
        from pathlib import Path
        from fastapi.testclient import TestClient
        from faturaguard.main import create_app
        from faturaguard.config import settings

        object.__setattr__(settings, 'data_directory', Path(data_path))
        app = create_app()
        app.state.source_backed_agent = None
        app.state.workflow_agent._source_agent = None
        document = Path('resources/fixtures/baseline_invoice.xml').read_bytes()
        for _ in range(2):
            with TestClient(app) as client:
                response = client.post('/documents/validate',
                    files={'file': ('baseline.xml', document, 'application/xml')})
                assert response.status_code == 200
        print('native-lifecycle-ok', flush=True)
    """)
    # Çocuk süreç gerçek kullanıcı geçmişine yazmaz.
    with tempfile.TemporaryDirectory(prefix='faturaguard-native-') as directory:
        result = subprocess.run(
            [sys.executable, '-c', f'data_path = {directory!r}\n' + program],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            errors='replace',
            timeout=60,
        )
    assert result.returncode == 0, result.stderr[-1800:]
    assert 'native-lifecycle-ok' in result.stdout
