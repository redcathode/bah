import os
import tempfile
import subprocess
import random
import string

def create_pdf_from_latex_string(latex_string):
    """
    Creates a PDF file from a LaTeX string using tectonic.

    Args:
        latex_string: The LaTeX content as a string.

    Returns:
        The path to the generated PDF file.
    """
    temp_dir = "/tmp/bah2-documents/"
    os.makedirs(temp_dir, exist_ok=True)

    random_name = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    tex_filename = os.path.join(temp_dir, f"{random_name}.tex")
    pdf_filename = os.path.join(temp_dir, f"{random_name}.pdf")

    with open(tex_filename, "w") as tex_file:
        tex_file.write(latex_string)

    command = [
        "/home/red/bah2/tectonic",
        "-X",
        "compile",
        tex_filename,
        "-Z",
        "continue-on-errors",
        "--untrusted",
    ]
    subprocess.run(command, check=True, capture_output=True)

    return pdf_filename

if __name__ == "__main__":
    latex_input = r"""\documentclass{article}
\usepackage{amsmath}
\title{My Document}
\author{Roo}
\date{\today}
\begin{document}
\maketitle
\section{Introduction}
This is a sample document created from a LaTeX string.
[
    E=mc^2
]
\end{document}"""
    pdf_path = create_pdf_from_latex_string(latex_input)
    print(f"PDF created at: {pdf_path}")