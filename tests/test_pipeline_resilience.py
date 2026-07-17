import unittest

import numpy as np

from main import has_valid_frame, is_live_source


class DummyResult:
    def __init__(self, frame):
        self.orig_img = frame


class PipelineResilienceTests(unittest.TestCase):
    def test_live_sources_are_identified(self):
        self.assertTrue(is_live_source("rtsp://camera/stream"))
        self.assertTrue(is_live_source("https://camera/stream"))
        self.assertTrue(is_live_source(0))
        self.assertFalse(is_live_source("videos/demo.mp4"))

    def test_corrupt_frames_are_rejected(self):
        self.assertFalse(has_valid_frame(DummyResult(None)))
        self.assertFalse(has_valid_frame(DummyResult(np.array([]))))
        self.assertTrue(has_valid_frame(DummyResult(np.zeros((2, 2, 3), dtype=np.uint8))))


if __name__ == "__main__":
    unittest.main()
