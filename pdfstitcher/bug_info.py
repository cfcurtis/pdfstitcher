import platform, psutil
import yaml
import pikepdf
import zipfile
from pathlib import Path
from pdf_mangler import mangler
from tempfile import gettempdir
from pdfstitcher.utils import __version__, Config


def get_system_info() -> dict:
    """
    Gets info on hardware and OS.
    """
    # Adapted from https://stackoverflow.com/a/58420504
    try:
        info = {}
        info["platform"] = platform.system()
        info["platform-release"] = platform.release()
        info["platform-version"] = platform.version()
        info["architecture"] = platform.machine()
        info["processor"] = platform.processor()
        info["ram"] = str(round(psutil.virtual_memory().total / (1024.0**3))) + " GB"
        info["python-version"] = platform.python_version()
        info["python-implementation"] = platform.python_implementation()
        info["python-build"] = platform.python_build()
        info["pdfstitcher-version"] = __version__
    except Exception as e:
        print(_("Error getting system info: {}").format(e))

    # Return whatever was collected
    return info


def mangle_pdf(pdf: pikepdf.Pdf) -> str:
    """
    Mangles the current PDF file, then returns
    the hash of the mangled file (its filename).
    """
    try:
        print(_("Mangling PDF. This may take some time."))
        mglr = mangler.Mangler(pdf=pdf)
        mglr.mangle_pdf()
        mglr.save(gettempdir())

        return mglr.hash_name
    except Exception as e:
        print(_("Error mangling PDF: {}").format(e))
        return ""


def collect_and_zip(pdf: pikepdf.Pdf) -> str:
    """
    Collects the various pieces of information and zips them up.
    Returns a string with the path to the zip file.
    """
    tempdir = Path(gettempdir())
    sys_info = get_system_info()
    with open(tempdir / "info.yaml", "w") as f:
        yaml.dump(sys_info, f)
        yaml.dump(Config.combo, f)

    if pdf:
        mangled_pdf = mangle_pdf(pdf)

    with zipfile.ZipFile(tempdir / "bug_info.zip", "w", compression=zipfile.ZIP_DEFLATED) as zip:
        zip.write(tempdir / "info.yaml")
        if pdf:
            zip.write(tempdir / mangled_pdf)

    return tempdir / "bug_info.zip"


if __name__ == "__main__":
    print(yaml.dump(get_system_info()))
    print(yaml.dump(Config.combo))
