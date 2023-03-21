

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name='dicom_tree',
    version='0.0.1',
    author='Jeffrey Duda',
    author_email='jeff.duda@gmail.com',
    description='Simple DICOM related operations',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/jeffduda/dicom_tree',
    project_urls = {
        "Bug Tracker": "https://github.com/jeffduda/dicom_tree/issues"
    },
    license='MIT',
    packages=['dicom_tree'],
    install_requires=['pydicom']
)