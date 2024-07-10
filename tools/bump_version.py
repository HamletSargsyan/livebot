from datetime import date
import os
import sys
import changelog
from semver import Version


with open("version") as f:
    version = Version.parse(f.read())


def usage():
    print(
        f"Usage: python3 {sys.argv[0]} [ major | minor | patch | prerelease | build ]"
    )
    sys.exit(0)


match sys.argv[1].lower():
    case "major":
        version = version.bump_major()
    case "minor":
        version = version.bump_minor()
    case "patch":
        version = version.bump_patch()
    case "prerelease":
        version = version.bump_prerelease()
    case "build":
        version = version.bump_build()
    case arg:
        print(f"Unknown arg `{arg}`")
        sys.exit(1)

with open("version", "w") as f:
    f.write(str(version))


with open("CHANGELOG.md", "r") as f:
    changes = changelog.loads(f.read())

for change in changes:
    if str(change["version"]).lower() == "unreleased":
        change["version"] = version
        change["date"] = date.today()
        changes.insert(
            0,
            {
                "version": "Unreleased",
            },
        )
        break


with open("CHANGELOG.md", "w") as f:
    f.write(changelog.dumps(changes))


os.system(f"git tag v{version}")
print(f"New tag created: v{version}")
