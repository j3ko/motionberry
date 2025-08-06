import os
from setuptools import setup, find_packages

version = {}
with open(os.path.join("app", "version.py")) as fp:
    exec(fp.read(), version)
version = version["__version__"]

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

install_requires = [
    "Flask==3.1.0",
    "numpy==1.26.3",
    "Pillow==11.0.0",
    "PyYAML==6.0.2",
    "Requests==2.32.3",
    "apispec==6.8.1",
    "apispec-webframeworks==1.2.0",
    "marshmallow==3.24.1",
    "opencv-python==4.10.0.84",
]

setup(
    name="motionberry",
    version=version,
    author="j3ko",
    author_email="j3ko@users.noreply.github.com",
    description="A lightweight solution for motion detection and video streaming on Raspberry Pi, powered by picamera2.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/j3ko/motionberry",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(where=".", include="app.*"),
    python_requires=">=3.6",
    install_requires=install_requires,
)