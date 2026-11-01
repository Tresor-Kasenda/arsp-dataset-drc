import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rccm_merge as m  # noqa: E402

FX = json.load(open(Path(__file__).parent / "fixtures" / "rccm_sample.json", encoding="utf-8"))


def test_rccm_key_handles_arsp_variants():
    assert m.rccm_key("CD/LSH/RCCM/26-B-03097") == ("LSH", "26", "B", "3097")
    assert m.rccm_key("CD/KZI/ RCCM/ 20 A 1035") == ("KZI", "20", "A", "1035")
    assert m.rccm_key("CD/KIN/RCCM/14-B-02478") == m.rccm_key("CD/KIN/RCCM/14-B-2478")
    assert m.rccm_key("CD/ISIRO/RCCM/13-B-1016/2019")[1:] == ("13", "B", "1016")
    assert m.rccm_key("n/a") is None


def test_flatten_and_sectors():
    rows = {a["_name"]: m.flatten(a) for a in FX}
    assert rows["KARIBU MINING DRC"]["sector_primary"] == "Mines & forage"
    assert rows["ASCHBEL CONSTRUCTION"]["sector_primary"] == "Construction & BTP"
    assert rows["DORIS KM GROUP"]["sector_primary"] == "Commerce & fournitures"
    assert rows["DORIS KM GROUP"]["idnat"] == "10-G4701-N18524J"
    assert "access" not in rows["DORIS KM GROUP"]


def test_province_by_ressort_needs_evidence():
    arsp = [{"rccm": f"CD/LSH/RCCM/21-B-{i:05d}", "province": "Haut-Katanga"} for i in range(1, 8)]
    arsp += [{"rccm": "CD/XYZ/RCCM/21-B-00001", "province": "Lualaba"}]  # un seul exemple : ignoré
    assert m.province_by_ressort(arsp) == {"LSH": "Haut-Katanga"}
