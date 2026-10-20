"""Game-competence calculators: pure pre-renewal formulas pinned to rathena.

Every expectation below is HAND-COMPUTED from the pinned rathena source at
``rathena/src/map/status.cpp`` (submodule e985006171d2) and the pinned
``rathena/db/pre-re/`` data files. The iro-db cross-check at the bottom reads
the git-ignored live corpus when present and skips when it is not.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from robots.knowledge.calculators import (
    aspd_pct,
    atk_with_weapon,
    base_atk,
    equip_projection,
    flee,
    hit,
    matk_max,
    matk_min,
    max_hp,
    max_sp,
    soft_def,
    soft_mdef,
)

NOVICE_STATS = {"str_": 9, "agi": 1, "vit": 1, "int_": 1, "dex": 9, "luk": 1}


class TestMaxHp:
    """status.cpp:3511-3546 status_calc_maxhp_pc; call site 4353."""

    def test_novice_level10_vit1(self) -> None:
        # base_hp[9] = 85 (db/pre-re/job_basepoints.yml Novice Level: 10 Hp: 85);
        # dmax = 85 * (1 + 1*0.01) = 85.85 -> uint32 truncation -> 85.
        assert max_hp(85, vit=1) == 85

    def test_vit0_no_multiplier(self) -> None:
        assert max_hp(85, vit=0) == 85

    def test_vit40_truncates(self) -> None:
        # IEEE double semantics, exactly as the C formula: 1.0 + 40*0.01 lands
        # on 1.3999999999999999 (exact tie rounds to even), so 85 * that is
        # 118.99999999999999 -> uint32 truncation -> 118 (not the naive 119).
        assert max_hp(85, vit=40) == 118

    def test_equip_vit_adds_one_hp_per_point(self) -> None:
        # status.cpp:3532 "Vit from equip gives +1 additional HP"
        assert max_hp(85, vit=1, equip_vit=5) == 85 + 5


class TestMaxSp:
    """status.cpp:3562-3590 status_calc_maxsp_pc; call site 4366."""

    def test_novice_level10_int1(self) -> None:
        # base_sp[9] = 20 (job_basepoints.yml Novice group BaseSp Level: 10)
        assert max_sp(20, int_=1) == 20

    def test_int30_truncates(self) -> None:
        # 20 * (1 + 30*0.01) = 26.0 -> 26
        assert max_sp(20, int_=30) == 26


class TestBaseAtk:
    """status.cpp:2424-2495 status_base_atk; PRE-RENEWAL BL_PC branch 2486-2490.

    dstr = str / 10; str += dstr*dstr; str += dex/5 + luk/5  (integer division).
    """

    def test_novice_stats(self) -> None:
        # dstr = 9//10 = 0; 9 + 0 + 9//5 + 1//5 = 9 + 0 + 1 + 0 = 10
        assert base_atk(9, 9, 1) == 10

    def test_floor_dstr_quadratic(self) -> None:
        # str 30: dstr = 3, 30 + 9 + 0 + 0 = 39
        assert base_atk(30, 0, 0) == 39

    def test_minimum_one_stat(self) -> None:
        assert base_atk(1, 1, 1) == 1


class TestWeaponAtk:
    """Projected attack = batk + weapon atk + equip atk (pre-re batk + rhw.atk)."""

    def test_knife3_on_novice(self) -> None:
        # Knife [3] id 1201: Attack: 17 (db/pre-re/item_db_equip.yml:2269)
        assert atk_with_weapon(17, 9, 9, 1) == 27

    def test_equip_atk_bonus_added(self) -> None:
        assert atk_with_weapon(17, 9, 9, 1, equip_atk=3) == 30


class TestMatk:
    """status.cpp:2511-2516 status_base_matk_min/max (PRE-RENEWAL).

    min = int + (int/7)^2 ; max = int + (int/5)^2.
    """

    def test_int1_flat(self) -> None:
        assert matk_min(1) == 1
        assert matk_max(1) == 1

    def test_int30(self) -> None:
        assert matk_min(30) == 30 + (30 // 7) ** 2  # 30 + 16 = 46
        assert matk_max(30) == 30 + (30 // 5) ** 2  # 30 + 36 = 66


class TestAspd:
    """status.cpp:2403-2413 status_base_amotion_pc PRE-RENEWAL branch.

    amotion = job aspd_base (weapon); amotion -= amotion*(4*agi+dex)/1000;
    displayed ASPD = 200 - amotion/10.
    """

    def test_novice_dagger(self) -> None:
        # Dagger base 650 (db/pre-re/job_aspd.yml Novice group BaseASPD Dagger);
        # 650*(4*1+9)//1000 = 8 -> amotion 642 -> 200 - 64.2 = 135.8
        assert aspd_pct(650, 1, 9) == pytest.approx(135.8)

    def test_higher_agi(self) -> None:
        # 650*(4*16+9)//1000 = 650*73//1000 = 47 -> 603 -> 200 - 60.3 = 139.7
        assert aspd_pct(650, 16, 9) == pytest.approx(139.7)


class TestHitFlee:
    """status.cpp:2704-2711 status_calc_misc PRE-RENEWAL: hit = level + dex;
    flee = level + agi."""

    def test_hit_flee_novice_level10(self) -> None:
        assert hit(10, 9) == 19
        assert flee(10, 1) == 11


class TestSoftDef:
    """status.cpp:2713-2719 status_calc_misc PRE-RENEWAL: def2 += vit;
    mdef2 += int + vit/2."""

    def test_novice(self) -> None:
        assert soft_def(1) == 1
        assert soft_mdef(1, 1) == 1

    def test_tanky(self) -> None:
        assert soft_def(40) == 40
        assert soft_mdef(30, 20) == 40


# ---- item-effect projection (criterion 4) ------------------------------------

# SMALL snapshots of the real git-ignored iro-db corpus rows (iro-db.db,
# entities.fields_json), transcribed 2026-10-15 by run/knowledge/iro-db/build_iro_db.py.
# These fixture literals are test data, NOT the corpus: the corpus itself is
# never committed.
CHRYSLIS_FIELDS = {
    "type": "Misc",
    "subtype": "General",
    "weight": "1",
    "required_level": "0",
    "buying_price": "--",
    "selling_price": "4 Z (4 Z)",
    "description": "Skin from a larva that has been shed or peeled off.",
}
KNIFE_FIELDS = {"type": "Weapon", "subtype": "Dagger", "attack": "17"}
SHIRT_FIELDS = {"type": "Armor", "defense": "1"}


class TestEquipProjection:
    def test_misc_item_no_equip_bonus(self) -> None:
        projection = equip_projection({"id": 915, "name": "Chrysalis", **CHRYSLIS_FIELDS})
        assert projection["kind"] == "misc"
        assert projection["sell_price_z"] == 4
        assert projection["equip_delta"] == {}
        assert "sellable 4z" in projection["line"]
        assert "no bonus" in projection["line"]

    def test_weapon_projects_atk_delta(self) -> None:
        projection = equip_projection(
            {"id": 1201, "name": "Knife [3]", **KNIFE_FIELDS}, stats=NOVICE_STATS
        )
        assert projection["kind"] == "weapon"
        assert projection["equip_delta"] == {"atk": 17}
        assert projection["projected_atk"] == 27  # batk 10 + knife 17
        # sell defaults to buy//2 when the corpus omits a sell price
        assert projection["sell_price_z"] is None

    def test_armor_projects_def_delta(self) -> None:
        projection = equip_projection({"id": 2302, "name": "Cotton Shirt", **SHIRT_FIELDS})
        assert projection["kind"] == "armor"
        assert projection["equip_delta"] == {"def": 1}

    def test_rathena_style_fields_accepted(self) -> None:
        # db/pre-re/item_db.yml shape: Buy: 8 with no Sell -> sell 4
        projection = equip_projection({"id": 915, "name": "Chrysalis", "Type": "Etc", "Buy": 8})
        assert projection["kind"] == "misc"
        assert projection["buy_price_z"] == 8
        assert projection["sell_price_z"] == 4  # default: buy//2


# ---- live-corpus cross-check (criterion 9) ------------------------------------


def test_novice_kills_a_real_corpus_poring_in_a_few_hits(tmp_path, monkeypatch):
    """Cross-check the projected atk against the corpus monster HP.

    Reads the git-ignored iro-db corpus read-only when present; skips when it
    is not (fresh clones, CI).
    """
    corpus = Path.cwd() / "run/knowledge/iro-db/iro-db.db"
    if not corpus.exists():
        pytest.skip("iro-db corpus absent")
    row = (
        sqlite3.connect(f"file:{corpus}?mode=ro", uri=True)
        .execute("SELECT fields_json FROM entities WHERE id = 1002 AND section = 'monsters'")
        .fetchone()
    )
    assert row is not None
    fields = json.loads(row[0])
    assert fields["hp"] == "60"  # Poring HP per the live corpus
    hard_def = int(fields["def"].split("+")[0].strip())  # "2 + 1 0.45%" -> 2

    atk = atk_with_weapon(17, str_=9, dex=9, luk=1)  # novice + Knife [3]
    per_hit = max(1, atk - hard_def)
    hits = -(-int(fields["hp"].replace(",", "")) // per_hit)
    assert 2 <= hits <= 4, f"expected a few hits, got {hits} (atk {atk}, def {hard_def})"
