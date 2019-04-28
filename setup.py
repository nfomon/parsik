import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="parsik",
    version="0.9.1",
    author="Mike Biggs",
    author_email="nfomon@users.noreply.github.com",
    description="A minimalistic PEG parser",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nfomon/parsik",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    keywords=['parser', 'parsing', 'peg', 'grammar', 'language'],
)
