import unittest

from etas_challenge.geonet_catalog import parse_fdsn_text


class GeoNetCatalogTest(unittest.TestCase):
    def test_parses_by_header_name_and_orders_events(self):
        lines = [
            "#EventID|Time|Latitude|Longitude|Depth/km|Magnitude|MagType|EventType\n",
            "b|2008-01-02T03:04:05.600Z|-40.1|174.2|12.5|4.3|M|earthquake\n",
            "a|2008-01-01T00:00:00Z|-41|173|3|4.0|ML|earthquake\n",
        ]
        events = parse_fdsn_text(lines)
        self.assertEqual([event.event_id for event in events], ["a", "b"])
        self.assertEqual(events[1].time_utc.isoformat(), "2008-01-02T03:04:05.600000+00:00")
        self.assertEqual(events[0].magnitude, 4.0)

    def test_skips_invalid_data_rows(self):
        lines = [
            "#EventID|Time|Latitude|Longitude|Depth/km|Magnitude|MagnitudeType|EventType\n",
            "bad|not-a-time|-40|174|5|4.1|M|earthquake\n",
        ]
        self.assertEqual(parse_fdsn_text(lines), [])


if __name__ == "__main__":
    unittest.main()
