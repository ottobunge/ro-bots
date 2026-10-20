"""Read-only allowlisted projection of exact test-world resources."""

import json
import subprocess
import sys
from pathlib import Path

if sys.flags.optimize != 0:
    raise RuntimeError("optimized helper execution refused")

SCRATCH = Path("/home/otto/.hermes/cache/scratch")
inventory = json.loads((SCRATCH / "playing-mvp-engine-inventory.json").read_text())
ids = [row["id"] for row in inventory["containers"]]
assert len(ids) == len(set(ids)) == 4 and not inventory["foreign_volume_users"]
assert all(
    row["test_project"] and row["test_volume_mounted"]
    for row in inventory["containers"]
)
database = [c for c in inventory["containers"] if c["database_service"]]
assert len(database) == 1 and database[0]["database_mount"]
format_container = (
    '{"id":{{json .Id}},"name":{{json .Name}},"image_id":{{json .Image}},'
    '"service":{{json (index .Config.Labels "com.docker.compose.service")}},'
    '"project":{{json (index .Config.Labels "com.docker.compose.project")}},'
    '"state_details":{{json .State}},"user":{{json .Config.User}},'
    '"mounts":{{json .Mounts}}}'
)


def query(command):
    result = subprocess.run(command, capture_output=True, timeout=12, check=False)
    if result.returncode:
        raise RuntimeError("Sanitized read-only engine query failed")
    return result.stdout.decode("utf-8", "strict")


rows = []
for identity in ids:
    raw = json.loads(
        query(
            ["docker", "container", "inspect", "--format", format_container, identity]
        )
    )
    assert raw["id"] == identity and raw["project"] == "ro-bots-test"
    assert raw["service"] in {"mariadb", "rathena-login", "rathena-char", "rathena-map"}
    raw["state"] = raw["state_details"]["Status"]
    health = raw["state_details"].get("Health") or raw["state_details"].get(
        "Healthcheck"
    )
    raw["health"] = health.get("Status") if isinstance(health, dict) else None
    rows.append(
        {
            k: raw[k]
            for k in [
                "id",
                "name",
                "image_id",
                "service",
                "project",
                "state",
                "user",
                "health",
            ]
        }
        | {
            "mounts": [
                {k: mount.get(k) for k in ["Type", "Name", "Destination", "RW"]}
                for mount in raw["mounts"]
            ]
        }
    )
# Qualified deployment is a reviewed input, not proof of currently existing state.
service_roles = {"rathena-login": "login", "rathena-char": "char", "rathena-map": "map"}
assert len(rows) == 4 and {c["service"] for c in rows} == {"mariadb", *service_roles}
assert all(c["state"] == "running" for c in rows)
deployment = json.loads(
    (
        Path("/home/otto/dev/ro-bots")
        / "run/reviews/playing-mvp-qualified-deployment.json"
    ).read_text()
)
qualified = deployment["native_roles"]
assert len(qualified) == 3 and {r["role"] for r in qualified} == set(
    service_roles.values()
)
assert len({r["id"] for r in qualified}) == 3
approved = {r["role"]: r for r in qualified}
for container in rows:
    if container["service"] in service_roles:
        role = approved[service_roles[container["service"]]]
        assert container["id"] == role["id"]
        assert container["image_id"] == role["image"] == deployment["target_image"]
    else:
        mounts = container["mounts"]
        assert all(
            m["Type"] == "volume" and m["Name"] == "ro-bots-world-test" for m in mounts
        )
        assert any(m["Destination"] == "/var/lib/mysql" for m in mounts)
volume = json.loads(
    query(
        [
            "docker",
            "volume",
            "inspect",
            "--format",
            '{"name":{{json .Name}},"labels":{{json .Labels}}}',
            "ro-bots-world-test",
        ]
    )
)
assert volume["name"] == "ro-bots-world-test"
labels = volume["labels"] or {}
allowed_labels = {
    k: labels[k]
    for k in [
        "com.docker.compose.project",
        "com.docker.compose.volume",
        "ro-bots.world",
        "ro-bots.project",
    ]
    if k in labels
}
result = {
    "read_only": True,
    "volume": volume["name"],
    "ordinary_compose_labels": allowed_labels,
    "containers": rows,
    "foreign_volume_users": [],
    "custom_inventory_labels_match": inventory["volume_labels_match"],
    "custom_label_absence_is_not_by_itself_foreign_ownership": True,
    "database_account_ownership_and_offline_not_yet_verified": True,
    "not_a_deployment_receipt": True,
}
(SCRATCH / "playing-mvp-engine-preflight.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
