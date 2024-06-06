import pikepdf
import sys

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: show_box_info.py <input file>")
        sys.exit(1)

    input_file = sys.argv[1]
    pdf = pikepdf.open(input_file)
    for i, page in enumerate(pdf.pages):
        print(f"Page {i + 1}:")
        print(f"  MediaBox: {page.MediaBox}")
        print(
            f"  Dimensions: {(page.MediaBox[2] - page.MediaBox[0])/72} x {(page.MediaBox[3] - page.MediaBox[1])/72}"
        )
        for key in page.keys():
            if "Box" in key and any([bval != mval for bval, mval in zip(page[key], page.MediaBox)]):
                print(f"  {key}: {page[key]}")
        print()
    pdf.close()
