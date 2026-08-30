from datetime import datetime, timezone

from etas_challenge.jma_catalog import FERN_REGIONS, JMAEvent, parse_hypocenter_record


def test_parse_official_1983_example():
    event = parse_hypocenter_record(
        "J198301010036584  02  33467  09  139212  11  21  39 39V   111F  3104NEAR MIYAKEJIMA ISLAND     K"
    )

    assert event is not None
    assert event.time_utc == datetime(1982, 12, 31, 15, 36, 58, 400000, tzinfo=timezone.utc)
    assert event.latitude == 33 + 46.7 / 60
    assert event.longitude == 139 + 21.2 / 60
    assert event.depth_km == 21
    assert event.magnitude == 3.9
    assert event.magnitude_type == "V"


def test_fern_regions_use_half_open_geography_and_target_thresholds():
    event = JMAEvent(
        time_utc=datetime(2004, 1, 1, tzinfo=timezone.utc),
        latitude=40.0,
        longitude=142.0,
        depth_km=10.0,
        magnitude=4.5,
        magnitude_type="J",
        agency="J",
    )

    assert FERN_REGIONS[0].contains(event)
    assert not FERN_REGIONS[1].contains(event)
    assert not FERN_REGIONS[2].contains(event)
    assert FERN_REGIONS[2].contains(event, feature_catalog=True)


def test_missing_magnitude_is_omitted():
    assert parse_hypocenter_record("J198301010036584" + " " * 80) is None
