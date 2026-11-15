"""The 3D body: green by default, painted over only where something is flagged.

The model has twenty-three parts and the channels name only ten of them, so
every part is drawn with the worst reading in the group the legend puts it in.
The head and the feet are the proof of it: no channel names either one, so the
head can only turn red through the neck beside it, and the feet only through the
legs. Everything else stays green, including the arms and joints nothing
measures -- the legend beside the model is where "No reading" is spelled out.

A material's colour is invisible to the DOM, so these read the pixels the
browser actually rendered: the viewer is screenshotted and handed back to the
page to be classified by hue, and the body is located by its own colours.
"""

import base64

import dashboard as ui
from conftest import Backend
from playwright.sync_api import Page, expect

# The statuses, told apart by hue after the model's lighting has washed them:
# critical (#ff3b30, rendered near #d93a34) holds green and blue close together
# under a high red, warning (#edb65b) lifts green well above blue, and nominal
# (#30d158, rendered near #4eb85f) leads with green. The panel behind the model
# matches none of them, which is what makes the body findable.
DRAWN = """async (url) => {
  const img = new Image();
  await new Promise((ok, no) => { img.onload = ok; img.onerror = no; img.src = url; });
  const canvas = document.createElement('canvas');
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const context = canvas.getContext('2d');
  context.drawImage(img, 0, 0);
  const {data} = context.getImageData(0, 0, canvas.width, canvas.height);
  const rows = [];
  for (let y = 0; y < canvas.height; y++) {
    const row = {body: 0, critical: 0, warning: 0, nominal: 0};
    for (let x = 0; x < canvas.width; x++) {
      const i = (y * canvas.width + x) * 4;
      const r = data[i], g = data[i + 1], b = data[i + 2];
      if (Math.max(r, g, b) < 60 || Math.max(r, g, b) - Math.min(r, g, b) < 20) continue;
      if (r - g > 60 && Math.abs(g - b) < 40) row.critical++;
      else if (r - g > 10 && g - b > 40) row.warning++;
      else if (g > r + 10 && g > b + 10) row.nominal++;
      else continue;
      row.body++;
    }
    rows.push(row);
  }
  const add = (bands) => bands.reduce((total, row) => ({
    body: total.body + row.body,
    critical: total.critical + row.critical,
    warning: total.warning + row.warning,
    nominal: total.nominal + row.nominal,
  }), {body: 0, critical: 0, warning: 0, nominal: 0});
  // Rows holding more than a few drawn pixels are the body; its first and last
  // ten are the head and the feet.
  const body = rows.filter((row) => row.body > 4);
  return {total: add(rows), head: add(body.slice(0, 10)), feet: add(body.slice(-10))};
}"""


def drawn(page: Page) -> dict[str, dict[str, int]]:
    shot = page.locator(".vitals-dashboard-body-scan-viewer").screenshot()
    return page.evaluate(DRAWN, "data:image/png;base64," + base64.b64encode(shot).decode())


def settled(page: Page, holds, attempts: int = 20) -> dict[str, dict[str, int]]:
    """Sample until the render catches up: a reading reaches the DOM before the
    canvas has drawn its next frame."""
    counts = drawn(page)
    for _ in range(attempts):
        if holds(counts):
            return counts
        page.wait_for_timeout(400)
        counts = drawn(page)
    raise AssertionError(counts)


def colour(band: dict[str, int]) -> str:
    """The one colour a part of the body is drawn in."""
    assert band["body"] > 50, band
    for name in ("critical", "warning", "nominal"):
        if band[name] > 0.8 * band["body"]:
            return name
    return f"mixed {band}"


def test_the_body_is_green_until_a_group_is_flagged(dashboard: Page, backend: Backend) -> None:
    def group(name: str):
        """One legend row's status, e.g. "Upper body"."""
        return ui.region_status(ui.region(dashboard, name))

    # Nothing read: the whole body, head to feet, is drawn in the default green.
    counts = settled(dashboard, lambda c: c["total"]["body"] > 1000)
    assert colour(counts["head"]) == "nominal"
    assert colour(counts["feet"]) == "nominal"
    assert counts["total"]["critical"] == 0, counts["total"]
    assert counts["total"]["warning"] == 0, counts["total"]

    # A warning paints over the default, on its own group only.
    backend.post("heart_rate", 100 / 60, "s^-1")  # heart and chest: upper body
    expect(group("Upper body")).to_have_text("Warning")
    counts = settled(dashboard, lambda c: c["total"]["warning"] > 200)
    assert colour(counts["head"]) == "nominal", "a different group keeps the default"
    assert colour(counts["feet"]) == "nominal"

    # A nominal reading in that group does not clear it: the worst is drawn.
    backend.post("spo2", 0.98, "1")
    expect(group("Upper body")).to_have_text("Warning")
    counts = settled(dashboard, lambda c: c["total"]["warning"] > 200)

    # The head carries no channel of its own. It turns red through the neck,
    # which is the only part of its group that is measured.
    backend.post("jugular_strain_pct", 0.0205, "1")
    expect(group("Head & neck")).to_have_text("Critical")
    counts = settled(dashboard, lambda c: c["head"]["critical"] > 50)
    assert colour(counts["head"]) == "critical"
    assert counts["total"]["warning"] > 200, "the upper body keeps its own status"

    # The feet carry no channel either, and turn amber through the legs.
    backend.post("bone_ntx_pct_baseline", 0.30, "1")  # pelvis, thighs, lower legs
    expect(group("Lower body")).to_have_text("Warning")
    counts = settled(dashboard, lambda c: c["feet"]["warning"] > 50)
    assert colour(counts["feet"]) == "warning"
    assert colour(counts["head"]) == "critical", "head and neck stay critical"

    # Nothing measures the arms or the joints: they are left at the default
    # rather than given a colour the data does not support.
    expect(group("Arms")).to_have_text("No reading")
    expect(group("Joints")).to_have_text("No reading")
    assert counts["total"]["nominal"] > 200, counts["total"]
