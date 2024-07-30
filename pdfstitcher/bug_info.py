import platform, psutil
import yaml
import pikepdf

from pathlib import Path
from pdf_mangler import mangler
from pdfstitcher.utils import __version__, Config


def get_system_info() -> str:
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

    # Return whatever was collected as a yaml string
    return yaml.dump(info)


def mangle_pdf(pdf: pikepdf.Pdf, save_path: Path, progress_win: None) -> Path:
    """
    Mangles and saves the current PDF file, then returns
    the path to the mangled file.
    """
    if not pdf:
        return None

    try:
        # open a new copy of the input file
        pdf_copy = pikepdf.Pdf.open(pdf.filename)
        mglr = mangler.Mangler(pdf=pdf_copy)
        mangled_path = save_path / mglr.hash_name

        # don't re-mangle if the file already exists
        if mangled_path.exists():
            progress_win and progress_win.Update(progress_win.GetRange())
            return mangled_path

        mglr.updater = progress_win
        mglr.mangle_pdf()
        mglr.save(save_path)

        return mangled_path
    except InterruptedError:
        raise InterruptedError

    except Exception as e:
        print("Error mangling PDF: {}").format(e)
        return None


if __name__ == "__main__":
    print(yaml.dump(get_system_info()))
    print(yaml.dump(Config.combo))
