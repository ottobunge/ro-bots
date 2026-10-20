import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from robots.adapters.spawn_species import spawn_species


def test_parses_monster_lines_for_one_map(tmp_path):
    f = tmp_path / "prontera.txt"
    f.write_text(
        "prt_fild08,0,0\tmonster\tPoring\t1002,70\n"
        "prt_fild08,0,0\tmonster\tLunatic\t1063,20\n"
        "prt_fild08,0,0\tmonster_hidden\tHidden\t1002,1\n"
        "prontera,0,0\tmonster\tOther\t1002,1\n"
        "# a comment line\n"
        "prt_fild08,0,0\twarp\twarpname\t3,2,prt_fild08,170,375\n",
        encoding="utf-8",
    )
    assert spawn_species(f, "prt_fild08") == ("Poring", "Lunatic")


def test_unknown_map_is_empty(tmp_path):
    f = tmp_path / "prontera.txt"
    f.write_text("prt_fild08,0,0\tmonster\tPoring\t1002,70\n", encoding="utf-8")
    assert spawn_species(f, "glastheim") == ()
