# Blender Render Job — ComputeSwarm

This Docker image runs Blender in headless mode to render animation frames.

---

## Quick Test (Standalone)

```bash
docker build -t computeswarm/blender-render:latest .
mkdir -p input output
# copy your .blend file into input/scene.blend
docker run \
  -e FRAME_NUMBER=1 \
  -v $(pwd)/input:/workspace/input \
  -v $(pwd)/output:/workspace/output \
  computeswarm/blender-render:latest
```

---

## Preparing a `.blend` File

1. Open your scene in Blender.
2. Set up **Camera**, **Lights**, and **Render Settings** (resolution, samples, engine — Cycles or Eevee).
3. Save the file as `scene.blend`.
4. Make sure the output file path in Blender is **relative** or blank; the container overrides it via `-o /workspace/output/frame_####`.

---

## Submitting as a ComputeSwarm Job

When submitting via the ComputeSwarm API, split your animation into **multiple work units** (one per frame):

```json
{
  "name": "My Animation Render",
  "docker_image": "computeswarm/blender-render:latest",
  "command": "blender -b /workspace/input/scene.blend -o /workspace/output/frame_#### -f {FRAME_NUMBER}",
  "env_vars": {},
  "input_files": ["s3://.../scene.blend.tar.gz"],
  "work_unit_count": 250,
  "reward_per_unit": 2.5
}
```

The orchestrator replaces `{FRAME_NUMBER}` with the actual frame index for each work unit.

---

## Expected Output Files

Each work unit produces one frame image in `/workspace/output/`:

- `frame_0001.png` (or `.jpg`, `.exr`, depending on your Blender settings)
- `computeswarm-meta.json` (job metadata)

---

## Combining Frames into a Video

After downloading the aggregated results:

```bash
# Using ffmpeg (recommended)
ffmpeg -framerate 30 -i output/frame_%04d.png -c:v libx264 -pix_fmt yuv420p output.mp4

# Using Blender's own video sequence editor (optional)
blender -b -P create_video.py
```

---

## Environment Variables

| Variable      | Default | Description                     |
|---------------|---------|---------------------------------|
| `FRAME_NUMBER`| `1`     | Frame to render (overridden by scheduler) |

