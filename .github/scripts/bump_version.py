import json
import re
import subprocess
import sys


def get_latest_tag() -> str | None:
    try:
        # Get all tags sorted by version-like order
        result = subprocess.run(
            ["git", "tag", "--list", "--sort=-v:refname"],
            capture_output=True,
            text=True,
            check=True,
        )
        tags = result.stdout.strip().split("\n")
        return tags[0] if tags and tags[0] else None
    except Exception:
        return None


def parse_version(v_str: str) -> tuple[int, int, int, bool, int]:
    # Parses X.Y.Z-beta.N or X.Y.Z
    # Returns (major, minor, patch, is_beta, beta_num)
    core = v_str.split("-")[0]
    parts = list(map(int, core.split(".")))
    while len(parts) < 3:
        parts.append(0)

    is_beta = "-" in v_str and "beta" in v_str
    beta_num = -1
    if is_beta:
        match = re.search(r"beta\.(\d+)", v_str)
        if match:
            beta_num = int(match.group(1))

    return parts[0], parts[1], parts[2], is_beta, beta_num


def bump_version(
    current: str | None,
    bump_type: str,
    release_status: str,
    all_tags: list[str] | None = None,
) -> str:
    is_target_beta = release_status == "beta"

    if not current:
        if is_target_beta:
            return "1.0.0-beta.0"
        return "1.0.0"

    major, minor, patch, is_curr_beta, curr_beta_num = parse_version(current)

    # Find latest STABLE tag for base calculation
    latest_stable = (0, 0, 0)
    if all_tags:
        for t in all_tags:
            t = t.lstrip("v")
            if t and "-" not in t:
                s_major, s_minor, s_patch, _, _ = parse_version(t)
                latest_stable = (s_major, s_minor, s_patch)
                break
    else:
        try:
            res = subprocess.run(
                ["git", "tag", "--list", "--sort=-v:refname"],
                capture_output=True,
                text=True,
            )
            for t in res.stdout.strip().split("\n"):
                t = t.lstrip("v")
                if t and "-" not in t:
                    s_major, s_minor, s_patch, _, _ = parse_version(t)
                    latest_stable = (s_major, s_minor, s_patch)
                    break
        except Exception:
            pass

    # Calculate Target Stable Core
    if bump_type == "major":
        target_core = (latest_stable[0] + 1, 0, 0)
    elif bump_type == "minor":
        target_core = (latest_stable[0], latest_stable[1] + 1, 0)
    else:  # patch
        target_core = (latest_stable[0], latest_stable[1], latest_stable[2] + 1)

    target_core_str = f"{target_core[0]}.{target_core[1]}.{target_core[2]}"

    if is_target_beta:
        # If current version's core matches target_core and is a beta, increment beta_num
        current_core = (major, minor, patch)
        if current_core == target_core and is_curr_beta:
            return f"{target_core_str}-beta.{curr_beta_num + 1}"
        return f"{target_core_str}-beta.0"
    # Stable release
    # If we are currently on a beta for this EXACT core, just strip the beta
    # (e.g. 1.1.0-beta.5 -> 1.1.0)
    current_core = (major, minor, patch)
    if current_core == target_core and is_curr_beta:
        return target_core_str

    # Otherwise, if we were on an OLDER version, the target_core is already bumped
    return target_core_str


def update_files(new_version: str) -> None:
    # Update pyproject.toml
    with open("pyproject.toml") as f:
        content = f.read()
    # Match version = "X.Y.Z"
    content = re.sub(
        r'version\s*=\s*"[^"]+"',
        f'version = "{new_version}"',
        content,
        count=1,
    )
    with open("pyproject.toml", "w") as f:
        f.write(content)

    # Update manifest.json
    with open("custom_components/shielddns/manifest.json") as f:
        manifest = json.load(f)
    manifest["version"] = new_version
    with open("custom_components/shielddns/manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)

    bump_type_in = sys.argv[1].lower()
    release_status_in = sys.argv[2].lower()

    latest_tag_val = get_latest_tag()
    current_v_val = latest_tag_val.lstrip("v") if latest_tag_val else None

    new_v_val = bump_version(current_v_val, bump_type_in, release_status_in)

    update_files(new_v_val)

    # Write to file for GitHub Actions
    with open("VERSION.txt", "w") as f:
        f.write(new_v_val)

    print(f"Successfully bumped version to {new_v_val}")
