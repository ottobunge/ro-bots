"""Bounded regressions for the four first mechanics review defects."""

from pathlib import Path

import pytest
import yaml

from robots.adapters.mechanics_yaml import CatalogError, YamlMechanics
from tests.test_mechanics_yaml import sword, write_catalog


def test_null_jobs_is_empty_not_omitted_default(tmp_path):
    root = write_catalog(tmp_path, [sword(Jobs=None), sword(1102), sword(1103, Jobs={})])
    mechanics = YamlMechanics(root, ruleset="pre-re")
    null_item = mechanics.item_by_id(1101)
    omitted_item = mechanics.item_by_id(1102)
    empty_item = mechanics.item_by_id(1103)
    assert null_item is not None
    assert omitted_item is not None
    assert empty_item is not None
    assert null_item.jobs == empty_item.jobs == ()
    assert omitted_item.jobs == (("All", True),)
    assert null_item.classes == (("All", True),)
    assert null_item.price_tier is None
    assert "compatibility not evaluated" in null_item.digest_text


@pytest.mark.parametrize(
    ("item_id", "aegis_name"),
    [(410447, "C_Handiness_Telescope"), (410448, "C_Blink_Eyes_Cosmic")],
)
def test_real_renewal_null_jobs_records_remain_empty(item_id, aegis_name):
    root = Path(__file__).resolve().parents[1] / "rathena" / "db"
    source = yaml.safe_load((root / "re" / "item_db_equip.yml").read_text())
    row = next(row for row in source["Body"] if row["Id"] == item_id)
    assert "Jobs" in row
    assert row["Jobs"] is None
    assert "Classes" not in row
    mechanics = YamlMechanics(root, ruleset="re")
    item = mechanics.item_by_id(item_id)
    assert item is not None
    assert item.aegis_name == aegis_name
    assert item.jobs == ()
    assert item.classes == (("All", True),)
    assert item.price_tier is None
    assert mechanics.excluded_items == ((400276, "duplicate Trade field"),)
    assert mechanics.item_by_id(400276) is None


def test_null_classes_is_empty_not_omitted_default(tmp_path):
    root = write_catalog(tmp_path, [sword(Classes=None), sword(1102), sword(1103, Classes={})])
    mechanics = YamlMechanics(root, ruleset="pre-re")
    null_item = mechanics.item_by_id(1101)
    omitted_item = mechanics.item_by_id(1102)
    empty_item = mechanics.item_by_id(1103)
    assert null_item is not None
    assert omitted_item is not None
    assert empty_item is not None
    assert null_item.classes == empty_item.classes == ()
    assert omitted_item.classes == (("All", True),)
    assert null_item.jobs == (("All", True),)


@pytest.mark.parametrize("field", ["skill MaxLevel", "tree MaxLevel", "prerequisite Level"])
@pytest.mark.parametrize("level", [14, 20])
def test_rejects_native_overflow_before_database_cap(tmp_path, field, level):
    skills = [
        {"Id": 5, "Name": "SM_BASH", "Description": "Bash", "MaxLevel": 10},
        {"Id": 1, "Name": "NV_BASIC", "Description": "Basic Skill", "MaxLevel": 9},
    ]
    requirement = {"Name": "NV_BASIC", "Level": 1}
    entry = {"Name": "SM_BASH", "MaxLevel": 10, "Requires": [requirement]}
    if field == "skill MaxLevel":
        skills[0]["MaxLevel"] = level
    elif field == "tree MaxLevel":
        entry["MaxLevel"] = level
    else:
        requirement["Level"] = level
    root = write_catalog(tmp_path, [], skills, [{"Job": "Swordman", "Tree": [entry]}])
    with pytest.raises(CatalogError, match=field):
        YamlMechanics(root, ruleset="pre-re")


def test_native_limit_still_caps_legal_tree_and_prerequisite_levels(tmp_path):
    skills = [
        {"Id": 5, "Name": "SM_BASH", "Description": "Bash", "MaxLevel": 10},
        {"Id": 1, "Name": "NV_BASIC", "Description": "Basic Skill", "MaxLevel": 9},
        {"Id": 99, "Name": "LIMIT", "Description": "Boundary", "MaxLevel": 13},
    ]
    trees = [
        {
            "Job": "Swordman",
            "Tree": [
                {
                    "Name": "SM_BASH",
                    "MaxLevel": 13,
                    "Requires": [{"Name": "NV_BASIC", "Level": 13}],
                },
                {"Name": "LIMIT", "MaxLevel": 13},
            ],
        }
    ]
    mechanics = YamlMechanics(write_catalog(tmp_path, [], skills, trees), ruleset="pre-re")
    by_name = {skill.skill_id: skill for skill in mechanics.skills_for_class("Swordman")}
    assert by_name["SM_BASH"].max_level == by_name["SM_BASH"].database_max_level == 10
    assert by_name["SM_BASH"].prerequisites == (("NV_BASIC", 9),)
    assert by_name["LIMIT"].max_level == by_name["LIMIT"].database_max_level == 13


@pytest.mark.parametrize("identity", ["Id", "AegisName"])
@pytest.mark.parametrize("exclusion", ["PetArmor", "PetEgg", "duplicate Trade"])
@pytest.mark.parametrize("reverse", [False, True])
def test_excluded_source_rows_cannot_hide_duplicate_identity(
    tmp_path, identity, exclusion, reverse
):
    first = sword(1101)
    second = sword(1102)
    second[identity] = first[identity]
    if exclusion != "duplicate Trade":
        second["Type"] = exclusion
    else:
        second["Trade"] = {"NoDrop": True}
    items = [second, first] if reverse else [first, second]
    root = write_catalog(tmp_path, items)
    if exclusion == "duplicate Trade":
        path = root / "pre-re" / "item_db_equip.yml"
        path.write_text(
            path.read_text().replace("  Trade:\n", "  Trade: {NoTrade: true}\n  Trade:\n")
        )
    with pytest.raises(CatalogError, match="duplicate item Id or AegisName"):
        YamlMechanics(root, ruleset="pre-re")


@pytest.mark.parametrize("identity", ["Id", "AegisName"])
def test_collisions_between_only_excluded_rows_are_rejected(tmp_path, identity):
    first = sword(1101, Type="PetArmor")
    second = sword(1102, Type="PetEgg")
    second[identity] = first[identity]
    root = write_catalog(tmp_path, [first, second])
    with pytest.raises(CatalogError, match="duplicate item Id or AegisName"):
        YamlMechanics(root, ruleset="pre-re")
