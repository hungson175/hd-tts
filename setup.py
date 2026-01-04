"""
Setup script for VietVoice TTS package
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read version from __init__.py
def get_version():
    init_file = this_directory / "vietvoicetts" / "__init__.py"
    with open(init_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"\'')
    raise RuntimeError("Unable to find version string.")

setup(
    name="vietvoicetts",
    version=get_version(),
    author="Thai-Binh Nguyen",
    author_email="nguyenvulebinh@gmail.com",
    description="High-quality Text-to-Speech library for Vietnamese",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nguyenvulebinh/VietVoice-TTS",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
        "soundfile>=0.10.3",
        "pydub>=0.25.0",
        "tqdm>=4.64.0",
    ],
    extras_require={
        "cpu": [
            "onnxruntime>=1.15.0",
        ],
        "gpu": [
            "onnxruntime-gpu>=1.15.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vietvoice-tts=vietvoicetts.cli:main",
        ],
    },
    include_package_data=True,
    keywords="tts text-to-speech vietnamese voice synthesis ai ml",
    project_urls={
        "Bug Reports": "https://github.com/nguyenvulebinh/VietVoice-TTS/issues",
        "Source": "https://github.com/nguyenvulebinh/VietVoice-TTS",
        "Documentation": "https://github.com/nguyenvulebinh/VietVoice-TTS/blob/main/README.md",
    },
) 