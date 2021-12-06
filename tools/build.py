"""
Build the angular app and copy the relevant files to the backend to be served
"""

import subprocess
import os
import sys
import glob
import shutil

if (prePath := os.getenv('CHAD_EXCHANGE')) == None:
    raise KeyError("Please set the CHAD_EXCHANGE environment variable")

# Move to the angular frontend project and build
os.chdir(os.path.join(prePath, "frontend"))

res = subprocess.run(["ng", "build", "--base-href", "/static/", "--output-hashing=none"], stdout=sys.stdout)
if res.returncode != 0:
    raise ValueError("Angular build failed")

# Copy the files into the correct location
destStatic = os.path.join(prePath, "backend", "chadServer", "static")
destTemplates = os.path.join(prePath, "backend", "chadServer", "templates")
source = os.path.join(prePath, "frontend", "dist", "frontend")

jsFiles = [os.path.abspath(file) for file in glob.glob(os.path.join(source, "*.js"))]
txtFiles = [os.path.abspath(file) for file in glob.glob(os.path.join(source, "*.txt"))]
icoFiles = [os.path.abspath(file) for file in glob.glob(os.path.join(source, "*.ico"))]
cssFiles = [os.path.abspath(file) for file in glob.glob(os.path.join(source, "*.css"))]
htmlFiles = [os.path.abspath(file) for file in glob.glob(os.path.join(source, "*.html"))]

# Copy html files to templates
for file in htmlFiles:
    shutil.copy(file, destTemplates)

staticFiles = jsFiles + txtFiles + icoFiles + cssFiles
for file in staticFiles:
    shutil.copy(file, destStatic)