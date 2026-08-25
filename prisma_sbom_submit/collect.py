import glob
import os
import json
import subprocess
import tempfile
import sys
import shlex


def discover_python_projects(path):
    if os.path.exists(os.path.join(path, "pyproject.toml")):
        yield path
    for p in glob.glob("**/pyproject.toml", root_dir=path):
        yield os.path.dirname(os.path.join(path, p))


def generate_python_sbom(path):
    try:
        import cyclonedx_py
    except ImportError:
        raise Exception("Optional dependencies for python projects not installed, Install prisma-sbom-submit[python]")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Install project in fresh venv
        print(f"Create temporary environment at {tmpdir}")
        subprocess.check_call([sys.executable, "-m", "uv", "venv", tmpdir])
        print(f"Install project at {tmpdir}")
        subprocess.check_call([sys.executable, "-m", "uv", "pip", "install", "--python", tmpdir, path])
        print(f"Generate SBOM")
        sbom = subprocess.check_output([sys.executable, "-m", "cyclonedx_py", "environment", tmpdir])
        return json.loads(sbom.strip())


def discover_npm_projects(path):
    if os.path.exists(os.path.join(path, "package.json")):
        yield path
    for p in glob.glob("**/package.json", root_dir=path):
        yield os.path.dirname(os.path.join(path, p))


def generate_npm_sbom(path):
    cwd = os.getcwd()
    npm_tool_dir = os.path.join(cwd, ".sbom-npm-tools")
    npm = os.environ.get("NPM", "npm")
    # No idea why the explicit bash call is necessary, only way I could make it work on GitHub actions
    subprocess.check_call(["bash", "-c", f"{shlex.quote(npm)} install --global --prefix {shlex.quote(npm_tool_dir)} @cyclonedx/cyclonedx-npm"])
    try:
        os.chdir(path)
        subprocess.check_call(["bash", "-c", f"{shlex.quote(npm)} ci"])
        print(f"Generate SBOM")
        sbom = subprocess.check_output(["bash", "-c", f'{shlex.quote(os.path.join(npm_tool_dir, "bin", "cyclonedx-npm"))}'])
    finally:
        os.chdir(cwd)
    return json.loads(sbom.strip())


def auto_bom(path):
    for p in discover_python_projects(path):
        print(f"Discovered Python project at path {p}")
        yield generate_python_sbom(p)
    for p in discover_npm_projects(path):
        print(f"Discovered NPM project at path {p}")
        yield generate_npm_sbom(p)
