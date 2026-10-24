from studies.luxury_wallet.fetch import jsonstat_to_frame


def test_jsonstat_to_frame_maps_flat_index_to_dimension_codes():
    # 2 geos x 3 years, row-major: index = geo_pos * 3 + time_pos. One value missing (index 4).
    data = {
        "id": ["geo", "time"],
        "size": [2, 3],
        "dimension": {
            "geo": {"category": {"index": {"FR": 0, "IT": 1}}},
            "time": {"category": {"index": {"2022": 0, "2023": 1, "2024": 2}}},
        },
        "value": {"0": 10.0, "2": 12.0, "3": 20.0, "5": 22.0},
    }

    df = jsonstat_to_frame(data).set_index(["geo", "time"])["value"]

    assert df[("FR", "2022")] == 10.0
    assert df[("FR", "2024")] == 12.0
    assert df[("IT", "2022")] == 20.0
    assert df[("IT", "2024")] == 22.0
    assert ("IT", "2023") not in df.index
