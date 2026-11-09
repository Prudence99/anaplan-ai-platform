"""Copy the fictional Estate sample from the installed package into data/."""

from importlib.resources import files
from pathlib import Path
import shutil


source = files("anaplan_estate").joinpath("example", "caldergate-estate")
destination = Path("data/examples/caldergate-estate")
if not source.is_dir():
    raise SystemExit("Caldergate example is not included in the installed Anaplan Estate package")
if destination.exists():
    raise SystemExit(f"Refusing to overwrite existing example directory: {destination}")
destination.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, destination)
print(destination.resolve())
