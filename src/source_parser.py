# Vendored from UKGovernmentBEIS/reward-hacking-misalignment, MIT license.
# Revision 169c3c76a02e51092b4023a8c7baba38f41e2800, rl-envs/src/rh_envs/common.py
import re

def extract_code_and_files(completion: str) -> tuple[str, dict[str, str]]:
    """Extract solution code and any additional files from model output.

    Supports multiple formats:
    1. ```python ... ``` blocks
    2. <file path="...">...</file> tags
    3. # filename: ... comments in code blocks

    Returns:
        tuple of (solution_code, dict of {filepath: content})
    """
    extra_files: dict[str, str] = {}
    solution_code = ""

    # First, try to extract <file> tags
    file_pattern = re.compile(
        r'<file\s+path=["\']([^"\']+)["\']>\s*(.*?)\s*</file>', re.DOTALL
    )
    for match in file_pattern.finditer(completion):
        filepath = match.group(1)
        content = match.group(2).strip()
        if filepath == "solution.py" or filepath.endswith("/solution.py"):
            solution_code = content
        else:
            extra_files[filepath] = content

    # Remove file tags from completion for further processing
    completion_cleaned = file_pattern.sub("", completion)

    # Extract python code blocks
    code_pattern = re.compile(r"```python\n(.*?)```", re.DOTALL)
    code_blocks = code_pattern.findall(completion_cleaned)

    for block in code_blocks:
        # Check if block specifies a filename
        filename_match = re.match(r"#\s*filename:\s*(\S+)\n", block)
        if filename_match:
            filepath = filename_match.group(1)
            content = block[filename_match.end() :].strip()
            if filepath == "solution.py":
                solution_code = content
            else:
                extra_files[filepath] = content
        elif not solution_code:
            # First code block without filename is the solution
            solution_code = block.strip()

    # If no solution found in structured format, try to extract any code
    if not solution_code:
        generic_pattern = re.compile(r"```\n(.*?)```", re.DOTALL)
        matches = generic_pattern.findall(completion_cleaned)
        if matches:
            solution_code = matches[0].strip()
        else:
            solution_code = completion_cleaned.strip()

    return solution_code, extra_files
