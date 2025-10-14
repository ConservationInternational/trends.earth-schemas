from te_schemas.results import FileResults, URI


def test_fileresults_get_all_uris_primary_only(tmp_path):
    primary_path = tmp_path / "main.tar.gz"
    primary_path.write_text("data")
    fr = FileResults(name="unccd_report", uri=URI(uri=primary_path))
    uris = fr.get_all_uris()
    assert len(uris) == 1
    assert uris[0].uri == primary_path


def test_fileresults_get_all_uris_with_others(tmp_path):
    primary_path = tmp_path / "main.tar.gz"
    other1 = tmp_path / "extra1.json"
    other2 = tmp_path / "extra2.txt"
    for p in [primary_path, other1, other2]:
        p.write_text("x")
    fr = FileResults(
        name="unccd_report",
        uri=URI(uri=primary_path),
        other_uris=[URI(uri=other1), URI(uri=other2)],
    )
    uris = fr.get_all_uris()
    assert [u.uri for u in uris] == [primary_path, other1, other2]
