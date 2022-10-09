import pathlib

import setuptools

# The directory containing this file
HERE = pathlib.Path(__file__).parent
README = HERE / "README.md"


setuptools.setup(
    name="alphaconf",
    version="0.0.1",
    author="Krzysztof Magusiak",
    author_email="chrmag@poczta.onet.pl",
    description="Write simple scripts leveraging omegaconf",
    license="MIT",
    keywords="configuration omegaconf script",
    url="https://github.com/kmagusiak/alphaconf",
    packages=setuptools.find_packages(exclude=['tests']),
    long_description=README.read_text(),
    long_description_content_type='text/markdown',
    # https://pypi.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Environment :: Console",
    ],
    python_requires=">=3.8",
    setup_requires=[
        'setuptools_scm',
    ],
    use_scm_version={
        "local_scheme": "no-local-version",
    },
    install_requires=[
        'omegaconf>=2',
    ],
    extras_require={
        'color': ['colorama'],
        'dotenv': ['python-dotenv'],
        'invoke': ['invoke'],
        'toml': ['toml'],
    },
)
