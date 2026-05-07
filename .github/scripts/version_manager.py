import argparse
import glob
import json
import os
import re
import subprocess
from typing import Any


def find_manifest() -> str | None:
    matches = glob.glob("custom_components/*/manifest.json")
    return matches[0] if matches else None


def get_current_version(manifest_path: str | None) -> str:
    try:
        tags = (
            subprocess.check_output(["git", "tag"], stderr=subprocess.DEVNULL)
            .decode()
            .splitlines()
        )
        v_tags: list[dict[str, Any]] = []
        for tag in tags:
            tag = tag.strip()
            match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)(?:(b)(\d+)|(-dev)(\d+))?$", tag)
            if match:
                y, m, p, bp, bn, dp, dn = match.groups()
                v_tags.append(
                    {
                        "tag": tag,
                        "key": (
                            int(y),
                            int(m),
                            int(p),
                            (1 if bp else (0 if dp else 2)),
                            (int(bn) if bp else (int(dn) if dp else 0)),
                        ),
                    }
                )
        if v_tags:
            v_tags.sort(key=lambda x: x["key"], reverse=True)
            return str(v_tags[0]["tag"])
    except subprocess.CalledProcessError, IndexError, ValueError:
        pass
    if manifest_path and os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest_data: dict[str, Any] = json.load(f)
            return str(manifest_data.get("version", "1.0.0"))
    return "1.0.0"


def write_version(v: str, manifest_path: str | None) -> None:
    if manifest_path and os.path.exists(manifest_path):
        with open(manifest_path) as f:
            data = json.load(f)
        data["version"] = v
        with open(manifest_path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    # Update pyproject.toml if it exists
    if os.path.exists("pyproject.toml"):
        with open("pyproject.toml") as f:
            content = f.read()
        content = re.sub(
            r'^version\s*=\s*".*?"', f'version = "{v}"', content, flags=re.MULTILINE
        )
        with open("pyproject.toml", "w") as f:
            f.write(content)


def calculate_version(rtype: str, level: str, curr: str) -> str:
    match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)(?:(b)(\d+)|(-dev)(\d+))?$", curr)
    if not match:
        # Fallback for old CalVer or invalid versions
        return "1.5.0"

    major_str, minor_str, patch_str, b_p, b_n_str, d_p, d_n_str = match.groups()
    major, minor, patch = int(major_str), int(minor_str), int(patch_str)
    snum = int(b_n_str) if b_p else (int(d_n_str) if d_p else 0)
    stype = "b" if b_p else ("-dev" if d_p else None)

    if rtype == "stable":
        if stype:  # Current is a pre-release (beta/dev), make it stable
            return f"{major}.{minor}.{patch}"
        # Current is stable, bump according to level
        if level == "major":
            return f"{major + 1}.0.0"
        if level == "minor":
            return f"{major}.{minor + 1}.0"
        return f"{major}.{minor}.{patch + 1}"

    if rtype == "beta":
        if stype == "b":
            return f"{major}.{minor}.{patch}b{snum + 1}"
        # Bump core to target level and start beta
        if level == "major":
            return f"{major + 1}.0.0b0"
        if level == "minor":
            return f"{major}.{minor + 1}.0b0"
        return f"{major}.{minor}.{patch + 1}b0"

    if rtype in ["dev", "nightly"]:
        if stype == "-dev":
            return f"{major}.{minor}.{patch}-dev{snum + 1}"
        # Bump core and start dev
        if level == "major":
            return f"{major + 1}.0.0-dev0"
        if level == "minor":
            return f"{major}.{minor + 1}.0-dev0"
        return f"{major}.{minor}.{patch + 1}-dev0"

    raise ValueError(f"Unknown type: {rtype}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["get", "bump"])
    parser.add_argument("--type", choices=["stable", "beta", "nightly", "dev"])
    parser.add_argument("--level", choices=["major", "minor", "patch"], default="patch")
    parser.add_argument("--manifest", default=None)
    args = parser.parse_args()
    m_path = args.manifest or find_manifest()
    if args.action == "get":
        print(get_current_version(m_path))
    elif args.action == "bump":
        if not args.type:
            parser.error("--type is required for bump action")
        v_new = calculate_version(args.type, args.level, get_current_version(m_path))
        write_version(v_new, m_path)
        print(v_new)
