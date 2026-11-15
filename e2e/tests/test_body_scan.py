"""The 3D body: each part drawn in the colour of its legend group.

The model has twenty-three parts and the channels name only ten of them, so
every part is drawn with the worst reading in the group the legend puts it in.
That is what colours the feet, which no channel measures, and what keeps the
model from saying something different to the legend beside it.

These read the pixels the browser actually rendered, since a material's colour
is invisible to the DOM: the viewer is screenshotted and the image handed back
to the page to be counted. Thresholds are coarse on purpose -- the question is
"is this part red", not how many pixels of it are.
"""

import base64
import time

import dashboard as ui
from conftest import Backend
from playwright.sync_api import Page, expect

# The status tokens, told apart by hue: critical #ef6969 has green and blue
# close together under a high red; warning #edb65b lifts green well above blue;
# nominal #83d4ac leads with green. Anything near-grey is unread or ungraded.
BUCKETS = """async (url) => {
  const img = new Image();
  await new Promise((ok, no) => { img.onload = ok; img.onerror = no; img.src = url; });
  const canvas = document.createElement('canvas');
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const context = canvas.getContext('2d');
  context.drawImage(img, 0, 0);
  const {data} = context.getImageData(0, 0, canvas.width, canvas.height);
  const out = {critical: 0, warning: 0, nominal: 0, neutral: 0};
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i], g = data[i + 1], b = data[i + 2];
    const span = Math.max(r, g, b) - Math.min(r, g, b);
    if (Math.max(r, g, b) < 60) continue;
    if (span < 20) out.neutral++;
    else if (r - g > 60 && Math.abs(g - b) < 40) out.critical++;
    else if (r - g > 10 && g - b > 40) out.warning++;
    else if (g > r + 10 && g > b + 10) out.nominal++;
  }
  return out;
}"""
PAINTED = 200  # a part of this body is thousands of pixels; 200 is "not noise"


def drawn(page: Page) -> dict[str, int]:
    """How much of the model is drawn in each status colour."""
    shot = page.locator(".vitals-dashboard-body-scan-viewer").screenshot()
    return page.evaluate(BUCKETS, "data:image/png;base64," + base64.b64encode(shot).decode())


def drawn_once(page: Page, holds, timeout_s: float = 8.0) -> dict[str, int]:
    """Sample until the render settles: a reading reaches the DOM before the
    canvas has drawn its next frame."""
    deadline = time.monotonic() + timeout_s
    counts = drawn(page)
    while not holds(counts) and time.monotonic() < deadline:
        time.sleep(0.4)
        counts = drawn(page)
    assert holds(counts), counts
    return counts


def test_the_model_colours_each_part_by_its_legend_group(dashboard: Page, backend: Backend) -> None:
    def group(name: str):
        """One legend row's status, e.g. "Upper body"."""
        return ui.region_status(ui.region(dashboard, name))

    # Nothing read: the whole body is neutral, no part claims a status.
    counts = drawn_once(dashboard, lambda c: c["neutral"] > PAINTED)
    assert counts["critical"] == 0, counts
    assert counts["warning"] == 0, counts
    assert counts["nominal"] == 0, counts

    # A nominal reading on the chest colours its group green, where it used to
    # be left in the same grey as a part nothing had measured.
    backend.post("spo2", 0.98, "1")
    expect(group("Upper body")).to_have_text("Nominal")
    counts = drawn_once(dashboard, lambda c: c["nominal"] > PAINTED)
    assert counts["critical"] == 0 and counts["warning"] == 0, counts

    # A warning anywhere in that group replaces it: the worst reading is drawn.
    backend.post("heart_rate", 100 / 60, "s^-1")
    expect(group("Upper body")).to_have_text("Warning")
    counts = drawn_once(dashboard, lambda c: c["warning"] > PAINTED)
    assert counts["nominal"] == 0, "the group's worst wins, not its newest"

    # A second group is coloured on its own: critical head and neck, from a
    # channel that names only the neck.
    backend.post("jugular_strain_pct", 0.0205, "1")
    expect(group("Head & neck")).to_have_text("Critical")
    counts = drawn_once(dashboard, lambda c: c["critical"] > PAINTED)
    assert counts["warning"] > PAINTED, "the upper body keeps its own status"

    # The lower-body channels name the pelvis, thighs and lower legs. The feet
    # have no channel of their own and are coloured through the group.
    before = counts["warning"]
    backend.post("bone_ntx_pct_baseline", 0.30, "1")
    expect(group("Lower body")).to_have_text("Warning")
    counts = drawn_once(dashboard, lambda c: c["warning"] > before + PAINTED)
    assert counts["critical"] > PAINTED, "head and neck stay critical"

    # Nothing measures the arms or the joints, so they stay neutral rather than
    # being given a colour the data does not support.
    expect(group("Arms")).to_have_text("No reading")
    expect(group("Joints")).to_have_text("No reading")
    assert counts["neutral"] > PAINTED, counts
