# pimotion2

```bash
docker run --name pimotion2 \
  --privileged \
  -v <path to config.yml>:/pimotion2/config \
  -v <path to capture directory>:/pimotion2/captures \
  -v /run/udev:/run/udev:ro \
  -p 5000:5000 \
  pimotion2
```