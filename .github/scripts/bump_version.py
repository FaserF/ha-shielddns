import json
import re
import subprocess
import sys
from pathlib import Path


def get_current_version():
    manifest_path = Path("custom_components/shielddns/manifest.json")
    if not manifest_path.exists():
        return "1.0.0"
    with open(manifest_path) as f:
        data = json.load(f)
    return data.get("version", "1.0.0")


def has_tags():
    try:
        result = subprocess.run(
            ["git", "tag"], capture_output=True, text=True, check=True
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def bump_version(version, bump_type):
    # Handle versions like 1.0.0 or 1.0
    parts = version.split(".")
    while len(parts) < 3:
        parts.append("0")

    major = int(parts[0])
    minor = int(parts[1])
    patch = int(parts[2])

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1

    return f"{major}.{minor}.{patch}"


def update_files(new_version):
    # Update manifest.json
    manifest_path = Path("custom_components/shielddns/manifest.json")
    if manifest_path.exists():
        with open(manifest_path) as f:
            data = json.load(f)
        data["version"] = new_version
        with open(manifest_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    # Update pyproject.toml
    pyproject_path = Path("pyproject.toml")
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        new_content = re.sub(
            r'version = "[^"]+"', f'version = "{new_version}"', content, count=1
        )
        pyproject_path.write_text(new_content)


def main():
    if len(sys.argv) < 2:
        print("Usage: bump_version.py <patch|minor|major> [tag_selector]")
        sys.exit(1)

    bump_type = sys.argv[1].lower()

    if not has_tags():
        print("No tags found. Setting version to 1.0.0 for first release.")
        new_version = "1.0.0"
    else:
        current_version = get_current_version()
        new_version = bump_version(current_version, bump_type)
        print(f"Bumping version from {current_version} to {new_version}")

    update_files(new_version)
    print(f"Successfully updated files to version {new_version}")


if __name__ == "__main__":
    main()
