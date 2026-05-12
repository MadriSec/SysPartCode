#!/usr/bin/env python3

import os

def main():
    # Construct the path to the installed packages file
    container_name = os.getenv("CONTAINER_NAME", "default_container")
    installed_packages_file = f"/var/lib/libsec_tool/container_data/{container_name}.txt"

    # Print for debugging
    print(f"Reading installed packages from: {installed_packages_file}")

    packages = {}  # Dictionary to store package_name -> version

    # Read the file and parse lines
    try:
        with open(installed_packages_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue  # Skip empty lines

                # Split on '===', ignoring lines that don't match
                if "===" in line:
                    pkg_name, pkg_version = line.split("===", 1)
                    pkg_name = pkg_name.strip()
                    pkg_version = pkg_version.strip()
                    packages[pkg_name] = pkg_version
    except FileNotFoundError:
        print(f"Error: File not found: {installed_packages_file}")
        return

    # Print results
    print("\nInstalled packages and their versions:")
    for pkg_name, pkg_version in packages.items():
        print(f"  {pkg_name} -> {pkg_version}")


if __name__ == "__main__":
    main()

