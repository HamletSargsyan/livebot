import sys
import changelog

with open("CHANGELOG.md") as f:
    changes = changelog.load(f)[1]

# print(changelog.dumps([changes], "").strip())
sys.stdout.write(changelog.dumps([changes], "").strip())
sys.stdout.flush()
