import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from Core.avatar_rendered_gap_validation import audit_bounded_silhouette_gap


class AvatarRenderedGapValidationTests(unittest.TestCase):
    def render_mask(self, *, with_gap: bool) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "mask.png"
        image = Image.new("L", (200, 200), 0)
        draw = ImageDraw.Draw(image)
        draw.rectangle((60, 20, 140, 180), fill=255)
        if with_gap:
            draw.ellipse((94, 70, 106, 110), fill=0)
        image.save(path)
        return path

    def test_solid_surface_has_no_bounded_gap(self):
        report = audit_bounded_silhouette_gap(
            self.render_mask(with_gap=False),
            normalized_roi=(0.40, 0.20, 0.60, 0.80),
        )
        self.assertFalse(report["spatial_gap_detected"])
        self.assertEqual(
            report["status"],
            "PASS_NO_BOUNDED_BACKGROUND_GAP_IN_CORRIDOR",
        )

    def test_encoded_background_tunnel_fails(self):
        report = audit_bounded_silhouette_gap(
            self.render_mask(with_gap=True),
            normalized_roi=(0.40, 0.20, 0.60, 0.80),
        )
        self.assertTrue(report["spatial_gap_detected"])
        self.assertGreater(
            report["maximum_bounded_background_run_pixels"],
            2,
        )
        self.assertEqual(report["status"], "FAILED_VISIBLE_SPATIAL_GAP")

    def test_unbounded_background_outside_body_is_not_a_hole(self):
        report = audit_bounded_silhouette_gap(
            self.render_mask(with_gap=False),
            normalized_roi=(0.0, 0.0, 1.0, 1.0),
        )
        self.assertFalse(report["spatial_gap_detected"])


if __name__ == "__main__":
    unittest.main()

