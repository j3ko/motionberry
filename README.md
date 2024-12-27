# motionberry

```bash
docker run --name motionberry \
  --privileged \
  -v <path to config.yml>:/motionberry/config \
  -v <path to capture directory>:/motionberry/captures \
  -v /run/udev:/run/udev:ro \
  -p 5000:5000 \
  motionberry
```