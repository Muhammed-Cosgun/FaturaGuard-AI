"""Git teslimi: yerel Markdown bağlantıları, sır imzaları ve çalışma dosyaları."""

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {".py", ".md", ".txt", ".json", ".toml", ".yml", ".yaml", ".cmd", ".ps1", ".env", ".example"}
SECRET_PATTERNS = [re.compile(rb"AIza[0-9A-Za-z_-]{30,}"), re.compile(rb"gsk_[0-9A-Za-z]{35,}"),
                   re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
                   re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
                   re.compile(rb"github_pat_[A-Za-z0-9_]{40,}")]


def secret_signature(data):
    return any(pattern.search(data) for pattern in SECRET_PATTERNS)


def markdown_issues(path, root):
    source = path.read_text(encoding="utf-8")
    source = re.sub(r"```.*?```", "", source, flags=re.S)
    issues = []
    for destination in re.findall(r"\]\(([^)]+)\)", source):
        destination = destination.strip().strip("<>")
        parsed = urlsplit(destination)
        if parsed.scheme or destination.startswith("#"):
            continue
        target = (path.parent / unquote(parsed.path)).resolve()
        if not target.is_relative_to(root.resolve()) or not target.exists():
            issues.append({"check": "markdown_target", "file": str(path.relative_to(root)), "target": destination})
    return issues


def check(root=ROOT, history=False):
    result = subprocess.run(["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True)
    files = [name for name in result.stdout.decode("utf-8").split("\0") if name]
    issues = []
    for name in files:
        path = root / name
        if not path.is_file():
            issues.append({"check": "missing_tracked_file", "file": name})
            continue
        if (path.name.startswith(".env") and path.name != ".env.example") or path.suffix in {".sqlite3", ".pem", ".key", ".p12", ".pfx"}:
            issues.append({"check": "private_runtime_file", "file": name})
        if path.suffix in TEXT_EXTENSIONS and secret_signature(path.read_bytes()):
            issues.append({"check": "secret_signature", "file": name})
        if path.suffix == ".md":
            issues.extend(markdown_issues(path, root))
    checked = 0
    if history:
        objects = subprocess.check_output(["git", "rev-list", "--objects", "--all"], cwd=root).decode("utf-8").splitlines()
        for row in objects:
            oid, _, name = row.partition(" ")
            if not name or Path(name).suffix not in TEXT_EXTENSIONS:
                continue
            data = subprocess.check_output(["git", "cat-file", "blob", oid], cwd=root)
            checked += 1
            if secret_signature(data):
                issues.append({"check": "history_secret_signature", "file": name, "object": oid})
    return {"kind": "submission_hygiene", "tracked_files": len(files), "history_blobs_checked": checked,
            "passed": not issues, "issues": issues,
            "limitation": "Pattern scan only; not proof of absence of all secrets or sensitive screenshot content."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check(history=args.history)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
