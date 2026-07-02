import shutil, os, zipfile

project_dir = r"D:\Qmol-3"
release_name = "qmol-v2.0.0-windows"
release_dir = os.path.join(project_dir, "release")
release_zip = os.path.join(project_dir, release_name + ".zip")

if os.path.exists(release_dir):
    shutil.rmtree(release_dir)
if os.path.exists(release_zip):
    os.remove(release_zip)

os.makedirs(release_dir)

files = ["api.py", "config.py", "requirements.txt", "requirements-lite.txt", 
         "requirements-postgres.txt", "requirements-full.txt",
         "setup.bat", "start.bat", "build-apk.bat", "README.md"]
for f in files:
    src = os.path.join(project_dir, f)
    if os.path.exists(src):
        shutil.copy2(src, release_dir)

shutil.copytree(os.path.join(project_dir, "src"), os.path.join(release_dir, "src"))
shutil.copytree(os.path.join(project_dir, "tests"), os.path.join(release_dir, "tests"))
shutil.copytree(os.path.join(project_dir, "docs"), os.path.join(release_dir, "docs"))
shutil.copytree(os.path.join(project_dir, "deploy"), os.path.join(release_dir, "deploy"))

if os.path.exists(os.path.join(project_dir, "landing")):
    shutil.copytree(os.path.join(project_dir, "landing"), os.path.join(release_dir, "landing"))
if os.path.exists(os.path.join(project_dir, "demo_output.png")):
    shutil.copy2(os.path.join(project_dir, "demo_output.png"), release_dir)

with open(os.path.join(release_dir, "README-RELEASE.txt"), "w") as f:
    f.write("Q-Mol v2.0.0 Release\nRun setup.bat then start.bat\n")

shutil.make_archive(os.path.join(project_dir, release_name), "zip", release_dir)
size_mb = os.path.getsize(release_zip) / (1024 * 1024)
print(f"Created: {release_zip}")
print(f"Size: {size_mb:.2f} MB")

shutil.rmtree(release_dir)
