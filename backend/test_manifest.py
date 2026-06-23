import os

package_dir = r"D:\creditbridge\backend\venv\Lib"
search_term = "manifest.hocon"

print(f"Searching for files named '{search_term}' in {package_dir}...")

found = False
for root, dirs, files in os.walk(package_dir):
    for file in files:
        if file.lower() == search_term:
            file_path = os.path.join(root, file)
            print(f"Found manifest.hocon: {file_path}")
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    print("--- Content ---")
                    print(f.read())
                    print("---------------")
                found = True
            except Exception as e:
                print("Error reading:", e)
