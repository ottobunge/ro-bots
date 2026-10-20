"""Read-only YAML mechanics tests: tiny fixtures first, pinned catalogs second."""

from pathlib import Path

import pytest
import yaml

from robots.adapters.mechanics_yaml import CatalogError, YamlMechanics
from robots.ports.mechanics import MechanicsPort


def write_catalog(
    tmp_path: Path,
    items: list[dict],
    skills: list[dict] | None = None,
    trees: list[dict] | None = None,
    ruleset: str = "pre-re",
) -> Path:
    selected = tmp_path / ruleset
    selected.mkdir(parents=True, exist_ok=True)
    for filename, kind, version, body in (
        ("item_db_equip.yml", "ITEM_DB", 3, items),
        ("skill_db.yml", "SKILL_DB", 4, skills or []),
        ("skill_tree.yml", "SKILL_TREE_DB", 1, trees or []),
    ):
        (selected / filename).write_text(
            yaml.safe_dump(
                {"Header": {"Type": kind, "Version": version}, "Body": body}, sort_keys=False
            ),
            encoding="utf-8",
        )
    return tmp_path


def sword(item_id: int = 1101, **extra: object) -> dict:
    return {
        "Id": item_id,
        "AegisName": f"Sword_{item_id}",
        "Name": "Sword",
        "Type": "Weapon",
        "Attack": 25,
        "Locations": {"Right_Hand": True},
        "EquipLevelMin": 2,
        **extra,
    }


def test_loads_base_metadata_without_inventing_market_or_effects(tmp_path):
    root = write_catalog(
        tmp_path, [sword(Buy=100, MagicAttack=9, Defense=3, Script="bonus bStr,2;")]
    )
    mechanics = YamlMechanics(root, ruleset="pre-re")
    item = mechanics.item_by_name("Sword")
    assert item is not None
    assert item.item_id == 1101
    assert item.required_level == 2
    assert item.stat_effects == (("atk", 25), ("def", 3), ("matk", 9))
    assert item.price_tier is None
    assert item.locations == ("Right_Hand",)
    assert "Script" in item.unknown_effects
    assert "combo effects not loaded" in item.unknown_effects
    assert "market price unknown" in item.digest_text
    assert "base metadata" in item.digest_text
    assert "compatibility not evaluated" in item.digest_text


def test_duplicate_names_fail_closed_with_explicit_identity_lookup(tmp_path):
    root = write_catalog(tmp_path, [sword(1103), sword(1101), sword(1102)])
    mechanics = YamlMechanics(root, ruleset="pre-re")
    assert mechanics.item_by_name("Sword") is None
    assert mechanics.item_by_name(" sword ") is None
    by_id = mechanics.item_by_id(1102)
    by_aegis = mechanics.item_by_aegis_name("Sword_1101")
    assert by_id is not None
    assert by_aegis is not None
    assert by_id.aegis_name == "Sword_1102"
    assert by_aegis.item_id == 1101
    assert mechanics.item_by_id(99999) is None
    assert [item.item_id for item in mechanics.items_for_slot("weapon")] == [1101, 1102, 1103]


def test_normalizes_slots_but_preserves_restriction_masks(tmp_path):
    items = [
        sword(
            1101,
            Locations={"Both_Hand": True},
            Jobs={"Swordman": True},
            Classes={"Normal": True, "Upper": False},
            Gender="Male",
            EquipLevelMax=90,
        ),
        sword(1102, Type="Armor", Locations={"Head_Top": True, "Head_Mid": True}),
        sword(1103, Type="Armor", Locations={"Left_Hand": True}),
        sword(1104, Type="Armor", Locations={"Both_Accessory": True}),
        sword(1105, Type="PetArmor", Locations={}),
    ]
    mechanics = YamlMechanics(write_catalog(tmp_path, items), ruleset="pre-re")
    weapon = mechanics.item_by_id(1101)
    assert weapon is not None
    assert weapon.locations == ("Both_Hand",)
    assert weapon.jobs == (("Swordman", True),)
    assert weapon.classes == (("Normal", True), ("Upper", False))
    assert weapon.gender == "Male"
    assert weapon.maximum_level == 90
    assert weapon.card_slots == 0
    for item_id, slot in ((1102, "headgear"), (1103, "shield"), (1104, "accessory")):
        item = mechanics.item_by_id(item_id)
        assert item is not None
        assert item.slot == slot
    assert mechanics.item_by_id(1105) is None  # pet armor is not player equipment
    assert mechanics.items_for_slot("unknown") == ()


def test_rejects_unsupported_schema_instead_of_coercing_values(tmp_path):
    root = write_catalog(tmp_path, [sword(Attack=True)])
    with pytest.raises(CatalogError, match="Attack"):
        YamlMechanics(root, ruleset="pre-re")


def test_skills_use_only_direct_parent_trees_and_actual_requirements(tmp_path):
    skills = [
        {"Id": i + 1, "Name": name, "Description": name, "MaxLevel": maximum}
        for i, (name, maximum) in enumerate(
            [
                ("NV_BASIC", 9),
                ("NV_TRICKDEAD", 1),
                ("SM_BASH", 10),
                ("SM_MAGNUM", 10),
                ("KN_PIERCE", 10),
            ]
        )
    ]
    trees: list[dict] = [
        {
            "Job": "Novice",
            "Tree": [
                {"Name": "NV_BASIC", "MaxLevel": 9},
                {"Name": "NV_TRICKDEAD", "MaxLevel": 1, "Exclude": True},
            ],
        },
        {
            "Job": "Swordman",
            "Inherit": {"Novice": True},
            "Tree": [
                {"Name": "SM_BASH", "MaxLevel": 10},
                {
                    "Name": "SM_MAGNUM",
                    "MaxLevel": 13,
                    "BaseLevel": 7,
                    "JobLevel": 3,
                    "Requires": [
                        {"Name": "SM_BASH", "Level": 5},
                        {"Name": "NV_BASIC", "Level": 1},
                        {"Name": "NV_BASIC", "Level": 0},
                    ],
                },
            ],
        },
        {
            "Job": "Knight",
            "Inherit": {"Swordman": True},
            "Tree": [{"Name": "SM_BASH", "MaxLevel": 0}, {"Name": "KN_PIERCE", "MaxLevel": 5}],
        },
    ]
    mechanics = YamlMechanics(write_catalog(tmp_path, [], skills, trees), ruleset="pre-re")
    novice = mechanics.skills_for_class("Novice")
    assert {skill.skill_id for skill in novice} == {"NV_BASIC", "NV_TRICKDEAD"}
    swordman = mechanics.skills_for_class("Swordsman")
    assert swordman == mechanics.skills_for_class("Swordman")  # one explicit legacy alias
    assert {skill.skill_id for skill in swordman} == {"NV_BASIC", "SM_BASH", "SM_MAGNUM"}
    magnum = next(skill for skill in swordman if skill.skill_id == "SM_MAGNUM")
    assert magnum.max_level == 10  # cap tree max against DB max, like rAthena
    assert magnum.database_max_level == 10
    assert magnum.required_base_level == 7
    assert magnum.required_job_level == 3
    assert magnum.required_level == 7  # legacy field mirrors declared base requirement only
    assert magnum.prerequisites == (("SM_BASH", 5),)
    assert "effects/formulas unknown" in magnum.digest_text
    knight = mechanics.skills_for_class("Knight")
    assert {skill.skill_id for skill in knight} == {"SM_MAGNUM", "KN_PIERCE"}
    assert mechanics.skills_for_class("swordman") == ()
    assert mechanics.skills_for_class("MadeUpClass") == ()


@pytest.mark.parametrize("ruleset", ["pre-re", "re"])
def test_pinned_catalog_real_records(ruleset):
    root = Path(__file__).resolve().parents[1] / "rathena" / "db"
    mechanics = YamlMechanics(root, ruleset=ruleset)
    assert isinstance(mechanics, MechanicsPort)
    assert mechanics.item_by_name("Sword") is None
    sword_item = mechanics.item_by_id(1101)
    assert sword_item is not None
    assert sword_item.aegis_name == "Sword"
    assert sword_item.stat_effects == (("atk", 25), ("def", 0), ("matk", 0))
    assert sword_item.required_level == 2
    assert sword_item.price_tier is None
    assert sword_item.jobs[-2:] == (("Swordman", True), ("Thief", True))
    skills = {skill.skill_id: skill for skill in mechanics.skills_for_class("Swordman")}
    assert skills["SM_MAGNUM"].prerequisites == (("SM_BASH", 5),)
    assert skills["SM_MAGNUM"].required_base_level == 0
    assert skills["SM_MAGNUM"].required_job_level == 0
    assert skills["SM_MAGNUM"].max_level == 10
    assert "NV_TRICKDEAD" not in skills
    assert len(mechanics.source_hashes) == 3


def test_excludes_malformed_opaque_trade_row_without_choosing_duplicate_value(tmp_path):
    root = write_catalog(tmp_path, [sword(1101), sword(1102)])
    path = root / "pre-re" / "item_db_equip.yml"
    path.write_text(
        path.read_text().replace(
            "- Id: 1102", "- Trade: {NoDrop: true}\n  Trade: {NoTrade: true}\n  Id: 1102"
        )
    )
    mechanics = YamlMechanics(root, ruleset="pre-re")
    assert mechanics.item_by_id(1101) is not None
    assert mechanics.item_by_id(1102) is None
    assert mechanics.excluded_items == ((1102, "duplicate Trade field"),)


def test_rejects_skill_symlink_to_other_ruleset(tmp_path):
    root = write_catalog(tmp_path, [])
    write_catalog(tmp_path, [], ruleset="re")
    path = root / "pre-re" / "skill_db.yml"
    path.unlink()
    path.symlink_to(root / "re" / "skill_db.yml")
    with pytest.raises(CatalogError, match="mixed ruleset"):
        YamlMechanics(root, ruleset="pre-re")


@pytest.mark.parametrize(
    "override",
    [
        {"Jobs": False},
        {"Classes": "All"},
        {"Locations": {"Right_Hand": 1}},
        {"Gender": "Unknown"},
        {"Id": "1101"},
        {"Attack": -1},
        {"EquipLevelMin": 90, "EquipLevelMax": 2},
        {"Unexpected": 1},
    ],
)
def test_strict_item_metadata_types(tmp_path, override):
    root = write_catalog(tmp_path, [sword(**override)])
    with pytest.raises(CatalogError):
        YamlMechanics(root, ruleset="pre-re")


def test_scripts_remain_opaque_and_are_never_executed(tmp_path):
    marker = tmp_path / "must_not_exist"
    root = write_catalog(
        tmp_path,
        [
            sword(
                Script=f'__import__("pathlib").Path("{marker}").touch()',
                EquipScript="if (getrefine()>6) { bonus bStr,999; }",
            )
        ],
    )
    item = YamlMechanics(root, ruleset="pre-re").item_by_id(1101)
    assert item is not None
    assert item.stat_effects == (("atk", 25), ("def", 0), ("matk", 0))
    assert item.unknown_effects == ("Script", "EquipScript", "combo effects not loaded")
    assert not marker.exists()


@pytest.mark.parametrize(
    "mutation",
    [
        "Footer:\n  Imports:\n    - Path: db/re/item_db_equip.yml\n",
        "Header:\n  Type: SKILL_DB\n  Version: 4\nBody: []\n",
        "Header:\n  Type: ITEM_DB\n  Version: true\nBody: []\n",
        "Header:\n  Type: ITEM_DB\n  Version: 3\nBody: {}\n",
        "!!python/object/apply:os.system ['touch should-not-run']\n",
    ],
)
def test_rejects_imports_wrong_headers_and_unsafe_yaml(tmp_path, mutation):
    root = write_catalog(tmp_path, [])
    path = root / "pre-re" / "item_db_equip.yml"
    if mutation.startswith("Footer"):
        path.write_text(path.read_text() + mutation)
    else:
        path.write_text(mutation)
    with pytest.raises(CatalogError):
        YamlMechanics(root, ruleset="pre-re")


def test_rejects_duplicate_metadata_keys(tmp_path):
    root = write_catalog(tmp_path, [sword()])
    path = root / "pre-re" / "item_db_equip.yml"
    path.write_text(path.read_text().replace("Attack: 25", "Attack: 25\n  Attack: 999"))
    with pytest.raises(CatalogError, match="duplicate YAML key Attack"):
        YamlMechanics(root, ruleset="pre-re")


@pytest.mark.parametrize("profile", ["classic", "renewal", "PRE-RE", "../re"])
def test_requires_exact_ruleset_names(tmp_path, profile):
    with pytest.raises(CatalogError, match="ruleset"):
        YamlMechanics(tmp_path, ruleset=profile)


@pytest.mark.parametrize(
    "trees",
    [
        [{"Job": "Swordman", "Inherit": {"Unknown": True}}],
        [{"Job": "Swordman", "Tree": [{"Name": "MISSING", "MaxLevel": 1}]}],
        [{"Job": "Swordman"}, {"Job": "Swordman"}],
        [{"Job": "Swordman", "Tree": [{"Name": "SM_BASH", "MaxLevel": 1, "Exclude": 1}]}],
        [
            {
                "Job": "Swordman",
                "Tree": [
                    {
                        "Name": "SM_BASH",
                        "MaxLevel": 1,
                        "Requires": [{"Name": "UNKNOWN", "Level": 1}],
                    }
                ],
            }
        ],
    ],
)
def test_refuses_unknown_skill_tree_shapes(tmp_path, trees):
    skills = [{"Id": 5, "Name": "SM_BASH", "Description": "Bash", "MaxLevel": 10}]
    root = write_catalog(tmp_path, [], skills, trees)
    with pytest.raises(CatalogError):
        YamlMechanics(root, ruleset="pre-re")
