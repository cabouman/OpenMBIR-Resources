# OpenMBIR Resources

This repository provides links to the OpenMBIR family of software packages.
OpenMBIR is a family of open source packages for model-based iterative reconstruction (MBIR) of tomographic and other sensor data.
See the [usage page](https://cabouman.github.io/OpenMBIR-Resources/usage/) for download counts of the packages over time.

**[MBIRTorch CT:](https://github.com/cabouman/mbirtorch)**
with documentation [here](https://mbirtorch.readthedocs.io).
This is the newest, most flexible, and most efficient package, and it is based on PyTorch.
It offers:

- ease of use,
- multi-GPU reconstruction using a variety of platforms including NVIDIA GPUs, Apple Silicon GPUs, and AMD GPUs (untested),
- rapid and robust convergence,
- support for parallel, cone beam (both curved and flat detectors), helical, and multi-axis (laminography) geometries,
- 4D space-time reconstruction from standard scans,
- support for a growing number of standard CT scanners, including NSI, Zeiss Versa, and Zeiss Ultra,
- optimal view selection,
- the ability to easily add new geometries.

We believe it is state-of-the-art in both speed and quality for iterative reconstruction.
In August 2026 we moved from JAX to PyTorch because of memory efficiency, speed, GPU hardware support, and easier integration with a wide range of PyTorch based AI applications.

**[SVMBIR Parallel CT:](https://github.com/cabouman/svmbir)**
This is a python package for parallel and fan beam CT reconstruction. The code is very fast and easy to use with good [documentation](https://svmbir.readthedocs.io/en/latest/index.html). This code is useful for reconstructing any parallel beam data including X-ray synchrotron and electron microscopy tilt sequences.

**[Gaussian Mixture EM Clustering Algorithm:](https://github.com/cabouman/pygmcluster)**
This is a python package for estimating the order and parameters of a Gaussian mixture model from training data. It is a port of some earlier widely used [C code](https://engineering.purdue.edu/~bouman/software/cluster).


**[XCal CT:](https://github.com/cabouman/xcal)**
with documentation [here](https://xcal.readthedocs.io).
This is software for automated calibration of X-ray CT sources and scanners.



***Lagacy Code***

**[MBIRJAX CT:](https://github.com/cabouman/mbirjax)**
with documentation [here](https://mbirjax.readthedocs.io).
This is the legacy software on which MBIRTorch is based. It is written in JAX. Everything in MBIRJAX has been ported to MBIRTorch, so we recommend that all users migrate to the new package. Migration should be easy because the two share very similar APIs.

**[MBIR Cone Beam CT:](https://github.com/cabouman/mbircone)**
This is a python package for cone beam CT reconstruction. The code is fairly fast and easy to use. It also supports 4D and PnP reconstruction using CNN prior models.

**[MBIR Multislice Helical CT:](https://github.com/cabouman/mbirhelical)**
This is a python package for multislice helical scan CT reconstruction. This is the geometry used by typical medical scanners. This is raw C code. It is reasonably well written, but since it is C code, it requires some effort to build and use. We are hoping to put a python front end on this code and accelerate it in the future.

**[C-code:](https://github.com/cabouman/C-code)**
This is a simple C-code package for reading and writing TIFF images.

**[Legacy C-code:](http://engineering.purdue.edu/~bouman/OpenMBIR)**
This is a pointer to a web page containing some of the old C-code implementations that served as the basis for these newer open-source packages.
