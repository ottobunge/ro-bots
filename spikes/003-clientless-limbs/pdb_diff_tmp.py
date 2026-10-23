"""What is the 906th packet id? (the old module imported from the spikes dir)"""
import sys

sys.path.insert(0, "/home/otto/dev/ro-bots/spikes/003-clientless-limbs")
import packetdb as pdb_new  # noqa: E402

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "pdb_old", "/home/otto/dev/ro-bots/spikes/003-clientless-limbs/pdb_old_tmp.py"
)
mod_old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod_old)

new_keys = sorted(set(pdb_new.PACKET_DB) - set(mod_old.PACKET_DB))
gone = sorted(set(mod_old.PACKET_DB) - set(pdb_new.PACKET_DB))
common = sorted(set(pdb_new.PACKET_DB) & set(mod_old.PACKET_DB))
changed = {
    hex(k): (mod_old.PACKET_DB[k], pdb_new.PACKET_DB[k])
    for k in common
    if pdb_new.PACKET_DB[k] != mod_old.PACKET_DB[k]
}
print("new keys:", {hex(k): pdb_new.PACKET_DB[k] for k in new_keys})
print("gone:", {hex(k) for k in gone})
print("changed:", changed)
print("old count:", len(mod_old.PACKET_DB), "new count:", len(pdb_new.PACKET_DB))
